import osmnx as ox
import os
from time import perf_counter
import pandas as pd
from services.input_validation import dm_to_dd, validate_route_area, validate_input_data
from services.calculate_trails import calculate_trail_for_single, calculate_trail_for_trip, calculate_trail_for_kgm
from services.merge_routes import merge
from services.travel_length import prepare_nearest_nodes
from services.container_types import normalize_container_type, parse_container_types

def sort_data(G, lot_filtered_data, main_point, lot):
    sorted_data = lot_filtered_data # .sort_values(by='distance_to_main_point')

    return sorted_data

def add_lots(kp_data):
    lots = kp_data['Лот'].unique()

    return lots

def filtered_by_kgm(lot_sorted_data):
    # lot_sorted_data['Объем суточный КГМ'] = lot_sorted_data['Объем суточный КГМ'].astype("string")
    lot_car_data = lot_sorted_data[~lot_sorted_data['Объем суточный КГМ'].isnull()]

    # print('Filtered by kgm: ', lot_sorted_data.shape[0], lot_car_data.shape[0])

    return lot_car_data

def filtered_by_cars(lot_sorted_data, car):
    kinds = lot_sorted_data['Вид контейнера'].map(normalize_container_type)
    selected = kinds.isin(parse_container_types(car))
    lot_car_data = lot_sorted_data.loc[selected].copy()
    lot_car_data['Вид контейнера'] = kinds.loc[selected]
    return lot_car_data


def load_convert_coordinates(kp_data, lot):
    """
    Загружает координаты из файла и преобразует их из формата DM в DD.
    :param file_path: Путь к CSV-файлу с координатами
    :return: Список координат в формате (широта, долгота)
    """
    
    # Проверяем наличие необходимых столбцов
    if 'Координаты площадки (широта)' not in kp_data.columns or 'Координаты площадки (долгота)' not in kp_data.columns:
        raise ValueError("Файл должен содержать столбцы 'Координаты площадки (широта)' и 'Координаты площадки (долгота)'")
    
    kp_data = kp_data[~kp_data['Координаты площадки (широта)'].isnull()]

    # Преобразование координат
    kp_data['latitude_dd'] = kp_data['Координаты площадки (широта)'].apply(dm_to_dd)
    kp_data['longitude_dd'] = kp_data['Координаты площадки (долгота)'].apply(dm_to_dd)

    filtered_data = kp_data[kp_data['Лот'] == lot]

    # print('Lots sum: ', lot, filtered_data.shape[0])

    return filtered_data

def main(kp_data, auto_data, main_point, containers_data, working_time, accuracy, to_kg, distance, logging, barrier):
    """
    Основная функция: загружает координаты, преобразует их и строит маршрут.
    :param file_path: Путь к файлу с координатами.
    """

    calculation_started = perf_counter()
    kp_data = validate_input_data(kp_data, auto_data, containers_data, main_point, accuracy, logging)

    # Определяем лоты
    lots = add_lots(kp_data)

    # Определяем машины, которые могут вывозить данные площадки
    cars = list(zip(auto_data['Марка ТС'],
                    auto_data['Виды контейнеров'],
                    auto_data['Максимальный объём вместимости, м3'],
                    auto_data['Средняя скорость движения, км/ч'],
                    auto_data['Норматив времени работы 1 ТС в сутки, час'],
                    auto_data['Время разгрузки, мин'],
                    auto_data['Код ТС'],
                    auto_data['Средняя скорость движения в городе, км/ч']))
    # print(cars)
    if barrier == True:
        drive_type = "drive_service"
    else:
        drive_type = "drive"
    
    # Загрузка, преобразование координат по лотам
    logging.warning(f"Загружаем карту в радиусе {accuracy/1000} км от полигона {main_point}. Тип маршрута: {drive_type}. Это длительный процесс, не выключайте программу.")
    graph_started = perf_counter()
    G = ox.graph_from_point(center_point=main_point, dist=accuracy, network_type=drive_type)
    logging.info(f"Подготовка карты: {perf_counter() - graph_started:.3f} с.")
    lookup_started = perf_counter()
    coordinates = [main_point] + list(zip(
        kp_data['Координаты площадки (широта)'].map(dm_to_dd),
        kp_data['Координаты площадки (долгота)'].map(dm_to_dd)))
    point_count = prepare_nearest_nodes(G, coordinates)
    logging.info(f"Пакетный поиск дорожных узлов: {point_count} уникальных координат за {perf_counter() - lookup_started:.3f} с.")
    # Сохраняем прежние отчёты, если проверка данных или загрузка карты не удалась.
    for output_file in ('results/result.xlsx', 'results/result_optimized.xlsx'):
        if os.path.exists(output_file):
            os.remove(output_file)
    to_kg = to_kg * 100

    routes_started = perf_counter()
    for lot in lots:
        # Конвертируем координаты и фильтруем по лотам
        lot_filtered_data = load_convert_coordinates(kp_data, lot)
        # Сортируем по удалённости от стартовой площадки
        lot_sorted_data = sort_data(G, lot_filtered_data, main_point, lot)
        
        
        for car in cars:
            logging.info(f"Начинаем создавать маршруты для машины {car[0]} в лоте {lot}")
            kp_cars_data = filtered_by_cars(lot_sorted_data, car[1])

            if car[0] == 'КАМАЗ 43255-6010-69 (самосвал)':
                routes = filtered_by_kgm(lot_sorted_data)
            else:
                routes = kp_cars_data

            while not routes.shape[0] < 1:
                logging.info(f"Осталось {routes.shape[0]} контейнерных площадок для расчёта.")
                all_trails = []
                trails = []

                # Если бункер вывозится только полным
                
                if 'КАМАЗ 43255-3010' in car[0] or 'Бункеровоз' in car[0]:
                    try:
                        # logging.info(f"Применяем алгоритм calculate_trail_for_single для расчёта.")
                        routes, trails = calculate_trail_for_single(routes, containers_data, working_time, car, lot, G, main_point, to_kg, distance, logging)
                    except:
                        logging.error(f"Расчёт для машины {car[0]} в лоте {lot} прерван из-за ошибки.")
                        break
                # if  car[0] == 'КАМАЗ 43255-6010-69 (самосвал)':
                elif 'самосвал' in car[0]: # Если бункер вывозится только полным
                    try:
                        # logging.info(f"Применяем алгоритм calculate_trail_for_kgm для расчёта.")
                        routes, trails = calculate_trail_for_kgm(routes, containers_data, working_time, car, lot, G, main_point, to_kg, distance, logging)
                    except:
                        logging.error(f"Расчёт для машины {car[0]} в лоте {lot} прерван из-за ошибки.")
                        break
                else:
                    try:
                        # logging.info(f"Применяем алгоритм calculate_trail_for_trip для расчёта.")
                        routes, trails = calculate_trail_for_trip(routes, containers_data, working_time, car, lot, G, main_point, to_kg, distance, logging)
                    except:
                        logging.error(f"Расчёт для машины {car[0]} в лоте {lot} прерван из-за ошибки.")
                        break

                for trail in trails:
                    all_trails.append(trail)

                try:
                    trails_data = pd.read_excel('results/result.xlsx')
                    all_trails_df = pd.DataFrame(all_trails)

                    df = pd.concat([trails_data, all_trails_df], ignore_index=True)
                    df.to_excel('results/result.xlsx', index=False)
                    
                except:
                    os.makedirs('results', exist_ok=True)
                    output_file = f"results/result.xlsx"
                    all_trails_df = pd.DataFrame(all_trails)
                    all_trails_df.to_excel(output_file, index=False)

            logging.info(f"Расчёт для машины {car[0]} в лоте {lot} завершён.")


    logging.info(f"Расчёт рейсов и запись Excel: {perf_counter() - routes_started:.3f} с.")
    input_file = f"results/result.xlsx"
    output_file = f"results/result_optimized.xlsx"
    # sum_trails('results/result.xlsx', working_time, lot, car[0], logging)
    merge(input_file, output_file, working_time, logging)

    logging.warning(f"Расчёт всех марщрутов завершён!")
    logging.info(f"Полное время расчёта: {perf_counter() - calculation_started:.3f} с.")
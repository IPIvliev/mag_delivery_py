import osmnx as ox
import os
import pandas as pd
from services.calculate_trails import calculate_trail_for_single, calculate_trail_for_trip, calculate_trail_for_kgm
from services.merge_routes import merge

def sort_data(G, lot_filtered_data, main_point, lot):
    sorted_data = lot_filtered_data # .sort_values(by='distance_to_main_point')

    return sorted_data

# Переводим координаты
def dm_to_dd(dm):
    """
    Преобразует значение формата DM (градусы и десятичные минуты) в DD (десятичные градусы).
    :param dm: Строка в формате DM (например, 56.14.833)
    :return: Десятичные градусы (float)
    """
    coor = str(dm).replace(',', '.')

    coor_len = len(coor.split('.'))

    # print('Coor len: ', coor_len)

    if coor_len == 3:
        degrees, minutes_decimal, sec = dm.split('.')
        minutes_decimal = minutes_decimal + sec

        degrees = int(degrees)  # Градусы
        minutes = float(minutes_decimal) / 1000  # Перевод в десятичные минуты

        # Преобразование в десятичные градусы
        return degrees + minutes / 60
    else:
        return float(coor)

def add_lots(kp_data):
    lots = kp_data['Лот'].unique()

    return lots

def filtered_by_kgm(lot_sorted_data):
    # lot_sorted_data['Объем суточный КГМ'] = lot_sorted_data['Объем суточный КГМ'].astype("string")
    lot_car_data = lot_sorted_data[~lot_sorted_data['Объем суточный КГМ'].isnull()]

    # print('Filtered by kgm: ', lot_sorted_data.shape[0], lot_car_data.shape[0])

    return lot_car_data

def filtered_by_cars(lot_sorted_data, car):
    # print('Вид контейнера ', lot_sorted_data['Вид контейнера'])
    lot_sorted_data['Вид контейнера'] = lot_sorted_data['Вид контейнера'].astype("string")
    lot_sorted_data['Вид контейнера'] = lot_sorted_data['Вид контейнера'].str.strip()
    lot_sorted_data['Вид контейнера'] = lot_sorted_data['Вид контейнера'].str.replace(',', '.')
    print(car, type(car))

    if type(car) == float:
        kp_values = [str(car).strip().replace(',', '.')]
    elif type(car) == int:
        kp_values = [str(car)]
    else:
        kp_values = car.split(';')
        kp_values = [value.strip() for value in kp_values]
        kp_values = [value.replace(',', '.') for value in kp_values]
        kp_values = [str(value) for value in kp_values]
 
    # print(lot_sorted_data['Вид контейнера'])

    lot_car_data = lot_sorted_data[lot_sorted_data['Вид контейнера'].isin(kp_values)]

    # print('KP with container types: ', kp_values, lot_car_data.shape[0])

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

def main(kp_data, auto_data, main_point, containers_data, working_time, accuracy, to_kg, distance, logging):
    """
    Основная функция: загружает координаты, преобразует их и строит маршрут.
    :param file_path: Путь к файлу с координатами.
    """

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

    # Загрузка, преобразование координат по лотам
    logging.warning(f"Загружаем карту в радиусе {accuracy/1000} км от полигона. Это длительный процесс, не выключайте программу.")
    G = ox.graph_from_point(center_point=main_point, dist=accuracy, network_type='drive')
    to_kg = to_kg * 100

    for lot in lots:
        # Конвертируем координаты и фильтруем по лотам
        lot_filtered_data = load_convert_coordinates(kp_data, lot)
        # Сортируем по удалённости от стартовой площадки
        lot_sorted_data = sort_data(G, lot_filtered_data, main_point, lot)
        
        
        for car in cars:
            logging.info(f"Начинаем создавать маршруты для машины {car[0]} в лоте {lot} ")
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
                        routes, trails = calculate_trail_for_single(routes, containers_data, working_time, car, lot, G, main_point, to_kg, distance, logging)
                    except:
                        logging.error(f"Расчёт для машины {car[0]} в лоте {lot} прерван из-за ошибки.")
                        break
                # if  car[0] == 'КАМАЗ 43255-6010-69 (самосвал)':
                elif 'самосвал' in car[0]: # Если бункер вывозится только полным
                    try:
                        routes, trails = calculate_trail_for_kgm(routes, containers_data, working_time, car, lot, G, main_point, to_kg, distance, logging)
                    except:
                        logging.error(f"Расчёт для машины {car[0]} в лоте {lot} прерван из-за ошибки.")
                        break
                else:
                    try:
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


    input_file = f"results/result.xlsx"
    output_file = f"results/result_optimized.xlsx"
    # sum_trails('results/result.xlsx', working_time, lot, car[0], logging)
    merge(input_file, output_file, working_time, logging)

    logging.warning(f"Расчёт всех марщрутов завершён!")
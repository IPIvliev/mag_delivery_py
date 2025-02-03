import osmnx as ox
import os
# import logging
import pandas as pd
from services.draw_trails import plot_route_on_map
from services.travel_length import shortest_travel_length
from services.create_route import calculate_routes_iterrows, calculate_routes_itertuples
from services.calculate_trails import calculate_trail_for_single, calculate_trail_for_trip

# # main_point = (float(56.2509833), float(43.8318333)) # База
# main_point = (float(56.320699), float(43.564531)) # Полигон
# # Загрузка данных из файлов
# trails_path = 'test.xlsx'
# file_path = 'реестр КП (тер схема).xlsx'
# kp_data = pd.read_excel(file_path, sheet_name='КП')
# kgm_data = pd.read_excel(file_path, sheet_name='КГМ')
# auto_data = pd.read_excel(file_path, sheet_name='Авто')
# containers_data = pd.read_excel(file_path, sheet_name='Виды контейнеров')
# working_time = 720 # 720

def sort_data(G, lot_filtered_data, main_point, lot):
    # lot_filtered_data['distance_to_main_point'] = lot_filtered_data.apply(shortest_travel_length, axis = 1, args=(G, main_point))
    sorted_data = lot_filtered_data # .sort_values(by='distance_to_main_point')

    return sorted_data

# Переводим координаты
def dm_to_dd(dm):
    """
    Преобразует значение формата DM (градусы и десятичные минуты) в DD (десятичные градусы).
    :param dm: Строка в формате DM (например, 56.14.833)
    :return: Десятичные градусы (float)
    """
    degrees, minutes_decimal, sec = dm.split('.')
    minutes_decimal = minutes_decimal + sec

    degrees = int(degrees)  # Градусы
    minutes = float(minutes_decimal) / 1000  # Перевод в десятичные минуты

    # Преобразование в десятичные градусы
    return degrees + minutes / 60

def add_lots(kp_data):
    lots = kp_data['Лот'].unique()
    # print('lots: ', lots)

    return lots

def filtered_by_cars(lot_sorted_data, car):
    # print('lot_sorted_data: ', lot_sorted_data.shape[0])
    kp_values = car.split(';')
    kp_values = [value.strip() for value in kp_values]
    kp_values = [value.replace(',', '.') for value in kp_values]
    # kp_values = [value.replace(',', '.') for value in kp_values]
    kp_values = [str(value) for value in kp_values]
 
    lot_sorted_data['Вид контейнера'] = lot_sorted_data['Вид контейнера'].astype("string")
    lot_sorted_data['Вид контейнера'] = lot_sorted_data['Вид контейнера'].str.strip()
    lot_sorted_data['Вид контейнера'] = lot_sorted_data['Вид контейнера'].str.replace(',', '.')

    # print(lot_sorted_data['Вид контейнера'])

    lot_car_data = lot_sorted_data[lot_sorted_data['Вид контейнера'].isin(kp_values)]
    # lot_car_data = lot_sorted_data[lot_sorted_data['Вид контейнера'].isin(kp_values)]

    # all_trails_df = pd.DataFrame(lot_car_data)
    # all_trails_df.to_excel('test_cont_type.xlsx', index=False)

    print('KP with container types: ', kp_values, lot_car_data.shape[0])

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
    
    # Преобразование координат
    kp_data['latitude_dd'] = kp_data['Координаты площадки (широта)'].apply(dm_to_dd)
    kp_data['longitude_dd'] = kp_data['Координаты площадки (долгота)'].apply(dm_to_dd)

    filtered_data = kp_data[kp_data['Лот'] == lot]

    print('Lots sum: ', lot, filtered_data.shape[0])

    return filtered_data

# # Функция для вычисления времени, необходимого на движение между точками
# def calculate_travel_time(start_coords, end_coords, speed_kmh):
#     # Вычисление расстояния между двумя точками (координатами) в км
#     distance_km = geopy.distance.distance(start_coords, end_coords).km
#     # Время в часах
#     travel_time = distance_km / speed_kmh
#     return travel_time * 60  # Переводим в минуты

def main(kp_data, auto_data, main_point, containers_data, working_time, accuracy, logging):
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
    logging.warning(f"Загружаем карту в радиусе 50 км от полигона. Это длительный процесс, не выключайте программу.")
    G = ox.graph_from_point(center_point=main_point, dist=accuracy, network_type='drive')
    # G = ox.graph_from_point(center_point=main_point, dist=50000, network_type='all')

    for lot in lots:
        # logging.info(f"Начинаем создавать маршруты для лота: {lot}")
        # file_name = 'routes_'+ str(lot) +'.xlsx'
        # Конвертируем координаты и фильтруем по лотам
        lot_filtered_data = load_convert_coordinates(kp_data, lot)
        # Сортируем по удалённости от стартовой площадки
        # lot_sorted_data = lot_filtered_data
        lot_sorted_data = sort_data(G, lot_filtered_data, main_point, lot)
        
        
        for car in cars:
            logging.info(f"Начинаем создавать маршруты для машины {car[0]} в лоте {lot} ")
            kp_cars_data = filtered_by_cars(lot_sorted_data, car[1])
            
            routes = kp_cars_data
            while not routes.shape[0] < 1:
                logging.info(f"Осталось {routes.shape[0]} контейнерных площадок для рассчёта.")
                all_trails = []
                trails = []
                if car[0] == 'КАМАЗ 43255-3010-69, МК-4512-04' or car[0] == 'Бункеровоз':
                    routes, trails = calculate_trail_for_single(routes, containers_data, working_time, car, lot, G, main_point)
                else:
                    routes, trails = calculate_trail_for_trip(routes, containers_data, working_time, car, lot, G, main_point)
                # if trails == False:
                #     break

                all_trails.append(trails)

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

    logging.warning(f"Расчёт всех марщрутов завершён!")

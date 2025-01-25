import osmnx as ox
import networkx as nx
import pandas as pd
from services import plot_route_on_map
import geopy.distance
from geopy.distance import geodesic

main_point = (float(56.2509833), float(43.8318333))
poligon_point = (float(43.564531), float(56.320699))
# Загрузка данных из файлов
file_path = 'реестр КП (тер схема).xlsx'
kp_data = pd.read_excel(file_path, sheet_name='КП')
auto_data = pd.read_excel(file_path, sheet_name='Авто')
containers_data = pd.read_excel(file_path, sheet_name='Виды контейнеров')
working_time = 720

# Функция для вычисления расстояния от главной точки
def calculate_distance(row, main_point):
    point = (row['latitude_dd'], row['longitude_dd'])
    route_length_km = geodesic(main_point, point).km  # Расстояние в километрах

    # print(main_point, row['Адрес дома, здания'], row['latitude_dd'], row['longitude_dd'], route_length_km)
    
    return route_length_km

def shortest_travel_length(row, G, start_point):
    # G = ox.graph_from_place('Nizhniy Novgorod', network_type="drive")
    # G = ox.graph_from_point(center_point=main_point, dist=3000, network_type='drive')

    # Поиск ближайших узлов графа для начальной и конечной точки
    origin_node = ox.distance.nearest_nodes(G, X=start_point[1], Y=start_point[0])
    destination_node = ox.distance.nearest_nodes(G, X=row['longitude_dd'], Y=row['latitude_dd'])

    # Поиск кратчайшего пути по длине
    # route = nx.shortest_path(G, origin_node, destination_node, weight="length")

    # Вычисление длины маршрута в метрах
    route_length_meters = nx.shortest_path_length(G, origin_node, destination_node, weight="length")

    # Перевод длины в километры
    route_length_km = route_length_meters / 1000

    # row['distance_to_main_point'] = route_length_km

    # print(main_point, row['Адрес дома, здания'], row['latitude_dd'], row['longitude_dd'], route_length_km)

    return route_length_km

# def shortest_travel_length(origin_point, destination_point):
#     G = ox.graph_from_place(center_point=origin_point, network_type="drive")

#     # Поиск ближайших узлов графа для начальной и конечной точки
#     origin_node = ox.distance.nearest_nodes(G, X=origin_point[1], Y=origin_point[0])
#     destination_node = ox.distance.nearest_nodes(G, X=destination_point[1], Y=destination_point[0])

#     # Поиск кратчайшего пути по длине
#     # route = nx.shortest_path(G, origin_node, destination_node, weight="length")

#     # Вычисление длины маршрута в метрах
#     route_length_meters = nx.shortest_path_length(G, origin_node, destination_node, weight="length")

#     # Перевод длины в километры
#     route_length_km = route_length_meters / 1000

#     return route_length_km

def sort_data(G, lot_filtered_data, main_point):
    # lot_filtered_data['distance_to_main_point'] = lot_filtered_data.apply(calculate_distance, axis = 1, main_point=main_point) 
    lot_filtered_data['distance_to_main_point'] = lot_filtered_data.apply(shortest_travel_length, axis = 1, args=(G, main_point))
    # lot_filtered_data.apply(shortest_travel_length, axis = 1, args=(G, main_point))
    sorted_data = lot_filtered_data.sort_values(by='distance_to_main_point')

    # print('sort_data: ', sorted_data)

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

    return lots

def filtered_by_cars(lot_sorted_data, car):
    kp_values = car.split(';')
    kp_values = [value.strip() for value in kp_values]
    kp_values = [value.replace(',', '.') for value in kp_values]
    # print('kp_values', kp_values)
    lot_sorted_data['Вид контейнера'] = lot_sorted_data['Вид контейнера'].astype(str)

    # print("lot_sorted_data['Вид контейнера'] ", lot_sorted_data['Вид контейнера'])

    lot_car_data = lot_sorted_data[lot_sorted_data['Вид контейнера'].isin(kp_values)]

    # print('lot_car_data: ', lot_car_data)

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
    # print("For lot ", lot, filtered_data)

    
    # Возвращаем список координат
    # list_cors = list(zip(filtered_data['КП'], filtered_data['Адрес дома, здания'], filtered_data['latitude_dd'], filtered_data['longitude_dd'], filtered_data['Вид контейнера'], 
    #          filtered_data['Количество контейнеров'], filtered_data['Объем суточный'], filtered_data['Лот']))
    return filtered_data

# Функция для вычисления времени, необходимого на движение между точками
def calculate_travel_time(start_coords, end_coords, speed_kmh):
    # Вычисление расстояния между двумя точками (координатами) в км
    distance_km = geopy.distance.distance(start_coords, end_coords).km
    # Время в часах
    travel_time = distance_km / speed_kmh
    return travel_time * 60  # Переводим в минуты

# Функция для расчёта маршрутов с учетом времени загрузки и выгрузки
def calculate_routes(kp_cars_data, car, containers_data, G):
    routes = []

    # Получаем данные о транспортном средстве
    car_lable = car[0] # Марка ТС
    car_code = car[6] # Код ТС
    # car_containers_type = car[1] # Виды контейнеров
    max_capacity = car[2] # Максимальный объём вместимости, м3
    max_working_time = car[4] # Норматив времени работы 1 ТС в сутки, час
    unload_time = car[5] # Время разгрузки, мин
    speed_kmh = car[3] # Средняя скорость движения, км/ч
    
    # Для каждой контейнерной площадки
    iterrows = kp_cars_data.iterrows()
    print('iterrows: ', iterrows)
    _, next_row = next(iterrows)
    print('next_row: ', next_row)
    
    for _, start_row in iterrows:
        
        start_coords = (start_row['latitude_dd'], start_row['longitude_dd'])
        container_type = start_row['Вид контейнера']
        container_type = container_type.replace('.', ',')
        # print('start container_type: ', container_type)
        container_count = start_row['Количество контейнеров']
        
        # Получаем время загрузки для конкретного типа контейнера
        load_time = containers_data[containers_data['Вид контейнера'] == container_type]['Время загрузки,сек'].values[0]
        load_time_minutes = load_time * container_count / 60  # Общее время на загрузку всех контейнеров в минутах
        
        # Рассчитываем время на выгрузку
        unload_time_total = unload_time * container_count
        
        # Рассчитываем маршруты для всех остальных площадок (в том числе обратный маршрут)
        
        
        end_coords = (next_row['latitude_dd'], next_row['longitude_dd'])
        print('end_coords: ', end_coords)
        
        # Расчет времени на движение
        # travel_time = calculate_travel_time(start_coords, end_coords, speed_kmh)
        travel_time = shortest_travel_length(next_row, G, start_coords)
        
        # Составляем маршрут
        # total_time = load_time_minutes + travel_time
        routes.append({
            'Марка ТС': car_lable,
            'Начальная площадка': next_row['КП'],
            'Конечная площадка': start_row['КП'],
            'Расстояние движения (км)': travel_time,
            'Время загрузки (мин)': load_time_minutes,
            # 'Время выгрузки (мин)': unload_time_total,
            # 'Общее время (мин)': total_time
        })

        next_row = start_row
    
    # Преобразуем результаты в DataFrame для удобного просмотра
    routes_df = pd.DataFrame(routes)
    return routes_df

# def build_route(coordinates):
#     """
#     Строит маршрут между координатами по кратчайшему пути.
#     :param coordinates: Список координат (широта, долгота) в формате DD.
#     :return: Граф дорожной сети и маршрут.
#     """
#     # Загрузка карты вокруг первой точки
#     G = ox.graph_from_point(center_point=coordinates[0], dist=10000, network_type='drive')
    
#     # Преобразуем координаты в узлы дорожной сети
#     route = []
#     for i in range(len(coordinates) - 1):
#         # Определяем ближайшие узлы
#         origin = ox.nearest_nodes(G, X=coordinates[i][1], Y=coordinates[i][0])
#         destination = ox.nearest_nodes(G, X=coordinates[i + 1][1], Y=coordinates[i + 1][0])
        
#         # Рассчитываем кратчайший путь
#         shortest_path = nx.shortest_path(G, origin, destination, weight='length')
#         route.extend(shortest_path if not route else shortest_path[1:])  # Избегаем дублирования узлов
    
#     return G, route

def main(kp_data, auto_data, main_point):
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
                    auto_data['Код ТС']))

    # Загрузка, преобразование координат по лотам
    # G = ox.graph_from_place('Nizhniy Novgorod', network_type="drive")
    G = ox.graph_from_point(center_point=main_point, dist=40000, network_type='drive')

    for lot in lots:
        # Конвертируем координаты и фильтруем по лотам
        lot_filtered_data = load_convert_coordinates(kp_data, lot)
        # Сортируем по удалённости от стартовой площадки
        lot_sorted_data = sort_data(G, lot_filtered_data, main_point)

        # print('lot_sorted_data: ', lot_sorted_data)
        
        for car in cars:
            # print("Для машины ", car)
            kp_cars_data = filtered_by_cars(lot_sorted_data, car[1])

            # print(kp_cars_data)
            
            routes = calculate_routes(kp_cars_data, car, containers_data, G)

            print("routes: ", routes)
            

    # print(len(kps))
    
    # Построение маршрута
    # G, route = build_route(coordinates)
    
    # Визуализация маршрута
    # print(G)

    # plot_route_on_map(G, route)
    



# file_path = "coordinates.csv"
main(kp_data, auto_data, main_point)

# Применяем функцию для расчёта маршрутов
# routes_result = calculate_routes(kp_data, auto_data, containers_data)

# Выводим результат
# print(routes_result)
import osmnx as ox
import pandas as pd
from services.draw_trails import plot_route_on_map
from services.travel_length import shortest_travel_length
from services.create_route import calculate_routes_iterrows, calculate_routes_itertuples
# from scipy.spatial import distance_matrix
# from ortools.constraint_solver import pywrapcp, routing_enums_pb2

# def optimize_route_with_tsp(points):
#     """
#     Оптимизирует маршрут с помощью алгоритма коммивояжёра (TSP).
#     :param points: Список точек [(latitude, longitude), ...].
#     :return: Оптимизированный порядок точек.
#     """
#     # Создаем матрицу расстояний
#     dist_matrix = distance_matrix(points, points)

#     # Настройка TSP через Google OR-Tools
#     tsp_size = len(points)
#     manager = pywrapcp.RoutingIndexManager(tsp_size, 1, 0)
#     routing = pywrapcp.RoutingModel(manager)

#     def distance_callback(from_index, to_index):
#         from_node = manager.IndexToNode(from_index)
#         to_node = manager.IndexToNode(to_index)
#         return int(dist_matrix[from_node][to_node])

#     transit_callback_index = routing.RegisterTransitCallback(distance_callback)
#     routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
#     search_parameters = pywrapcp.DefaultRoutingSearchParameters()
#     search_parameters.first_solution_strategy = (
#         routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
#     )

#     # Решаем TSP
#     solution = routing.SolveWithParameters(search_parameters)
#     if not solution:
#         raise ValueError("Не удалось найти оптимальный маршрут")

#     # Получаем оптимизированный порядок точек
#     route = []
#     index = routing.Start(0)
#     while not routing.IsEnd(index):
#         route.append(manager.IndexToNode(index))
#         index = solution.Value(routing.NextVar(index))
#     return route

# def sort_data(G, lot_filtered_data, main_point, lot):
#     """
#     Оптимизирует сортировку данных площадок по минимальному маршруту.
#     """
#     print(lot)
#     file_name = 'optimized_order_'+ str(lot) +'.xlsx'
#     print(file_name)

#     points = lot_filtered_data[['latitude_dd', 'longitude_dd']].to_numpy().tolist()
#     points.insert(0, main_point)  # Включаем главную точку как начало маршрута
#     # print(points)

#     optimized_order = optimize_route_with_tsp(points)

#     # Переставляем данные по оптимальному маршруту
#     # sorted_data = lot_filtered_data.iloc[optimized_order[1:] - 1]  # Убираем главную точку
#     lot_filtered_data = lot_filtered_data.reset_index(drop=True)
#     sorted_data = lot_filtered_data.iloc[[i - 1 for i in optimized_order[1:]]]

#     sorted_data_df = pd.DataFrame(sorted_data)
#     sorted_data_df.to_excel(file_name, index=False)

#     return sorted_data

# main_point = (float(56.2509833), float(43.8318333)) # База
main_point = (float(56.320699), float(43.564531)) # Полигон
# Загрузка данных из файлов
file_path = 'реестр КП (тер схема).xlsx'
kp_data = pd.read_excel(file_path, sheet_name='КП')
auto_data = pd.read_excel(file_path, sheet_name='Авто')
containers_data = pd.read_excel(file_path, sheet_name='Виды контейнеров')
working_time = 720 # 720

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

    return lots

def filtered_by_cars(lot_sorted_data, car):
    kp_values = car.split(';')
    kp_values = [value.strip() for value in kp_values]
    kp_values = [value.replace(',', '.') for value in kp_values]
    # print('kp_values', kp_values)
    lot_sorted_data['Вид контейнера'] = lot_sorted_data['Вид контейнера'].astype(str)

    lot_car_data = lot_sorted_data[lot_sorted_data['Вид контейнера'].isin(kp_values)]

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

    return filtered_data

# # Функция для вычисления времени, необходимого на движение между точками
# def calculate_travel_time(start_coords, end_coords, speed_kmh):
#     # Вычисление расстояния между двумя точками (координатами) в км
#     distance_km = geopy.distance.distance(start_coords, end_coords).km
#     # Время в часах
#     travel_time = distance_km / speed_kmh
#     return travel_time * 60  # Переводим в минуты



def calculate_trail(routes, working_time, car, lot, G, main_point):
    
    copy_routes = routes.copy()
    iterrows = copy_routes.iterrows()
    _, next_row = next(iterrows)
    length_from_first_kp_to_polygon = float(next_row['Расстояние начальной КП от точки старта'])
    time_from_first_kp_to_polygon = length_from_first_kp_to_polygon / car[3] * 60

    # trails = []
    routes_list = ''
    car_time_out = float(car[5]) # Время разгрузки, мин
    trail_time = time_from_first_kp_to_polygon + car_time_out
    trail_length = length_from_first_kp_to_polygon
    trail_weight = 0
    routes_amount = 0
    car_max_weight = float(car[2])    
    # print('enumerate(routes): ', len(routes))

    remove_routes = []

    print('length ', len(copy_routes))

    for i, route in iterrows:
    # while not routes.empty:
        
        # print(route)
        try: 
            length_from_last_kp_to_polygon = float(route['Расстояние конечной КП до полигона'])
        except:
            length_from_last_kp_to_polygon = 37.0
            break

        time_from_last_kp_to_polygon = length_from_last_kp_to_polygon / car[3] * 60

        # print('(trail_time + time_from_last_kp_to_polygon): ', (trail_time + time_from_last_kp_to_polygon),  working_time, ((trail_time + time_from_last_kp_to_polygon) <= working_time),
        #       'trail_weight: ', trail_weight, car_max_weight, (trail_weight <= car_max_weight),
        #       'if: ', (((trail_time + time_from_last_kp_to_polygon) <= working_time) and (trail_weight <= car_max_weight)))

        if (((trail_time + time_from_last_kp_to_polygon) <= working_time) and (trail_weight <= car_max_weight)):
            print('pass ', i)

            
        else:
            # trail_time = trail_time - (length_from_last_kp_to_polygon / car[3] * 60)
            # print('Continue')
            continue
        
        routes_amount += 1
        routes_list += route['Адрес конечной площадки'] + '; '
        trail_time += float(route['Время движения (мин)']) + float(route['Время загрузки (мин)'])
        trail_weight += float(route['Общий объём контейнеров'])
        trail_length += float(route['Расстояние движения (км)'])

        remove_routes.append(i)

    copy_routes.drop(remove_routes, inplace=True)

    
    if not 'length_from_last_kp_to_polygon' in locals():
        length_from_last_kp_to_polygon = 37.0
        time_from_last_kp_to_polygon = length_from_last_kp_to_polygon / car[3] * 60

    print('length_from_last_kp_to_polygon ', length_from_last_kp_to_polygon)
        
    trails = {
        'Маршрут': routes_list,
        'Лот': lot,
        'Количество КП в маршруте': routes_amount,
        'Дистанция от полигона до 1 кп (км)': length_from_first_kp_to_polygon,
        'Время движения от полигона до 1 кп (мин)': time_from_first_kp_to_polygon,
        'Дистанция от последней КП до полигона (км)': length_from_last_kp_to_polygon,
        'Время движения от последней КП до полигона (мин)': time_from_last_kp_to_polygon,
        'Общее время движения (мин)': trail_time + time_from_last_kp_to_polygon,
        'Общая длина маршрута (км)': trail_length + length_from_last_kp_to_polygon,
        'Общий объём загрузки машины (м3)': trail_weight
    }

    return copy_routes, trails

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
                    auto_data['Код ТС'],
                    auto_data['Средняя скорость движения в городе, км/ч']))

    # Загрузка, преобразование координат по лотам
    G = ox.graph_from_point(center_point=main_point, dist=50000, network_type='drive')
    # G = ox.graph_from_point(center_point=main_point, dist=50000, network_type='all')

    for lot in lots:
        file_name = 'routes_'+ str(lot) +'.xlsx'
        # Конвертируем координаты и фильтруем по лотам
        lot_filtered_data = load_convert_coordinates(kp_data, lot)
        # Сортируем по удалённости от стартовой площадки
        # lot_sorted_data = lot_filtered_data
        lot_sorted_data = sort_data(G, lot_filtered_data, main_point, lot)
        
        
        for car in cars:
            kp_cars_data = filtered_by_cars(lot_sorted_data, car[1])
            
            try:
                routes = pd.read_excel(file_name)
            except:
                # routes = calculate_routes_iterrows(kp_cars_data, car, containers_data, G, lot, main_point)
                routes = calculate_routes_itertuples(kp_cars_data, car, containers_data, G, lot, main_point)

            all_trails = []
            while not routes.empty:
                routes, trails = calculate_trail(routes, working_time, car, lot, G, main_point)
                all_trails.append(trails)

            all_trails_df = pd.DataFrame(all_trails)
            all_trails_df.to_excel('test.xlsx', index=False)
            print("trails: ", all_trails_df)

main(kp_data, auto_data, main_point)
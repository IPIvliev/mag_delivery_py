from services.travel_length import shortest_travel_length, shortest_travel_length_iter
import pandas as pd

def culculate_load_time(container_type, container_count, containers_data):
    # Получаем время загрузки для конкретного типа контейнера
    container_type = container_type.replace('.', ',')
    load_time = containers_data[containers_data['Вид контейнера'] == container_type]['Время загрузки,сек'].values[0]
    load_time_minutes = load_time * container_count / 60  # Общее время на загрузку всех контейнеров в минутах

    return load_time_minutes

def calculate_trail(kp_data, containers_data, working_time, car, lot, G, main_point):
    
    # copy_kp_data = kp_data.copy()
    copy_kp_data = kp_data
    iterrows = copy_kp_data.itertuples(index = True)

    last_row = next(iterrows)

    print(last_row)

    # Получаем данные о транспортном средстве
    car_lable = car[0] # Марка ТС
    car_code = car[6] # Код ТС
    car_containers_type = car[1] # Виды контейнеров
    car_max_weight = car[2] # Максимальный объём вместимости, м3
    max_working_time = car[4] # Норматив времени работы 1 ТС в сутки, час
    car_time_unload = float(car[5]) # Время разгрузки, мин
    speed_road_kmh = car[3] # Средняя скорость движения, км/ч
    speed_city_kmh = car[7] # Средняя скорость движения в городе, км/ч

    routes_list = ''

    trail_time = car_time_unload
    trail_weight = 0
    trail_length = 0
    routes_amount = 0
    whole_containers_amount = 0
    load_time = 0

    # length_from_first_kp_to_polygon = float(next_row['Расстояние начальной КП от точки старта'])
    length_from_last_kp_to_polygon = shortest_travel_length_iter(last_row, G, main_point)
    time_from_last_kp_to_polygon = length_from_last_kp_to_polygon / speed_road_kmh * 60

    trail_length += length_from_last_kp_to_polygon
    trail_time += time_from_last_kp_to_polygon

    trail_weight += last_row[10]
    whole_containers_amount += last_row[9]
    load_time += culculate_load_time(last_row[8], last_row[9], containers_data)
    trail_time += load_time

    remove_routes = []

    print('length ', len(copy_kp_data))

    length_from_current_kp_to_polygon = 0
    time_from_current_kp_to_polygon = 0

    start_count_row = 0 # Индекс точки для определения амплитуды поиска

    for current_row in iterrows:

        # Составляем список столбцов из файла с кп
        last_kp_number = last_row[1] # № п\п	
        last_kp_comment = last_row[2] # коммент	
        last_kp_name = last_row[3] # КП	
        last_kp_latitude = last_row[4] # Координаты площадки (широта)	
        last_kp_longitude = last_row[5] # Координаты площадки (долгота)	
        last_kp_state = last_row[6] # Район обслуживания	
        last_kp_address = last_row[7] # Адрес дома, здания	
        last_kp_type = last_row[8] # Вид контейнера	
        last_kp_amount = last_row[9] # Количество контейнеров	
        last_kp_weight = last_row[10] # Объем суточный	
        last_kp_lot = last_row[11] # Лот

        current_row_coords = (current_row.latitude_dd, current_row.longitude_dd)
        current_trail_length = shortest_travel_length_iter(last_row, G, current_row_coords)
        current_trail_time = (current_trail_length / speed_city_kmh)

        current_trail_weight = trail_weight + float(current_row[10])

        current_load_time = culculate_load_time(current_row[8], current_row[9], containers_data)

        length_from_current_kp_to_polygon = shortest_travel_length_iter(current_row, G, main_point)
        time_from_current_kp_to_polygon = length_from_current_kp_to_polygon / speed_road_kmh * 60

        if (((trail_time + current_trail_time + current_load_time + time_from_current_kp_to_polygon) < working_time) and ((trail_weight + current_trail_weight )< car_max_weight)):
            trail_length += current_trail_length
            trail_time += current_trail_time + current_load_time
            load_time += current_load_time
            trail_weight += current_trail_weight
            whole_containers_amount += current_row[9]
            print('pass ', current_row[0])

            routes_amount += 1
            routes_list += current_row[7] + '; '

            remove_routes.append(current_row.Index)

            print('last_row, current_row', remove_routes) 
            last_row = current_row
            # print('last_row = current_row', last_row, current_row)
        else:
            # break
            if (start_count_row < 5):
                start_count_row += 1
                print('start_count_row ', start_count_row)
                continue
            else:
                start_count_row = 0
                print('break')
                break
        
    # print('!!!!!!!!!!!!!!!!/ncopy_kp_data.drop(remove_routes, inplace=True)/n', remove_routes)
    copy_kp_data.drop(remove_routes, inplace=True)

    trail_length += length_from_current_kp_to_polygon
    trail_time += time_from_current_kp_to_polygon
        
    trails = {
        'Время для сравнения': (trail_time + current_trail_time + current_load_time + time_from_current_kp_to_polygon),
        'Время работы': working_time,
        'Общая загрузка': (trail_weight + current_trail_weight ),
        'Максимальная загрузка': car_max_weight,
        'ID маршрута': '',
        'Лот': lot,
        'Название района': last_kp_state,
        'Состав маршрута': routes_list,
        'Тип контейнера': last_kp_type,
        'Тип машины': car_lable,
        'id машины': car_code,
        'Количество КП': routes_amount,
        'Количество контейнеров': whole_containers_amount,
        'Масса кг': whole_containers_amount * 0.83,
        'Общий объём загрузки машины (м3)': trail_weight,
        'Дистанция от полигона до 1 кп (км)': length_from_last_kp_to_polygon,
        'Дистанция между КП (км)': trail_length - length_from_last_kp_to_polygon - length_from_current_kp_to_polygon,
        'Дистанция от последней КП до полигона (км)': length_from_current_kp_to_polygon,
        'Средняя скорость машины (км/ч)': (speed_city_kmh + speed_road_kmh) / 2,
        'Время разгрузки (мин)': car_time_unload,
        'Общее время погрузки (час)': load_time / 60,
        'Время разгрузки (час)': car_time_unload / 60,
        'Время в движении (час)': trail_time - load_time - car_time_unload,
        'Общее время прохождения маршрута (час)': trail_time / 60,
        'Время стационарной работы (мин)': load_time + car_time_unload,
        'Длина маршрута (км)': trail_length,
        'Общее время маршрута (мин)': trail_time
    }

    return copy_kp_data, trails

# def calculate_trail(routes, working_time, car, lot, G, main_point):
    
#     copy_routes = routes.copy()
#     iterrows = copy_routes.iterrows()
#     print('iterrows: ', copy_routes)
#     _, next_row = next(iterrows)
#     length_from_first_kp_to_polygon = float(next_row['Расстояние начальной КП от точки старта'])
#     time_from_first_kp_to_polygon = length_from_first_kp_to_polygon / car[3] * 60

#     # trails = []
#     routes_list = ''
#     car_time_out = float(car[5]) # Время разгрузки, мин
#     trail_time = time_from_first_kp_to_polygon + car_time_out
#     trail_length = length_from_first_kp_to_polygon
#     trail_weight = 0
#     routes_amount = 0
#     car_max_weight = float(car[2])    
#     # print('enumerate(routes): ', len(routes))

#     remove_routes = []

#     print('length ', len(copy_routes))

#     for i, route in iterrows:
#     # while not routes.empty:
        
#         length_from_last_kp_to_polygon = float(route['Расстояние конечной КП до полигона'])

#         time_from_last_kp_to_polygon = length_from_last_kp_to_polygon / car[3] * 60

#         # print('(trail_time + time_from_last_kp_to_polygon): ', (trail_time + time_from_last_kp_to_polygon),  working_time, ((trail_time + time_from_last_kp_to_polygon) <= working_time),
#         #       'trail_weight: ', trail_weight, car_max_weight, (trail_weight <= car_max_weight),
#         #       'if: ', (((trail_time + time_from_last_kp_to_polygon) <= working_time) and (trail_weight <= car_max_weight)))
#         trail_weight += float(route['Общий объём контейнеров'])
#         trail_time += float(route['Время движения (мин)']) + float(route['Время загрузки (мин)'])

#         if (((trail_time + time_from_last_kp_to_polygon) <= working_time) and (trail_weight <= car_max_weight)):
#             print('pass ', i)
#         else:
#             # trail_time = trail_time - (length_from_last_kp_to_polygon / car[3] * 60)
#             # print('Continue')
#             continue
        
#         routes_amount += 1
#         routes_list += route['Адрес конечной площадки'] + '; '
        
#         trail_length += float(route['Расстояние движения (км)'])

#         remove_routes.append(i)

#     copy_routes.drop(remove_routes, inplace=True)

    
#     # if not 'length_from_last_kp_to_polygon' in locals():
#     #     length_from_last_kp_to_polygon = 37.0
#     #     time_from_last_kp_to_polygon = length_from_last_kp_to_polygon / car[3] * 60

#     print('length_from_last_kp_to_polygon ', length_from_last_kp_to_polygon)
        
#     trails = {
#         'Маршрут': routes_list,
#         'Лот': lot,
#         'Количество КП в маршруте': routes_amount,
#         'Дистанция от полигона до 1 кп (км)': length_from_first_kp_to_polygon,
#         'Время движения от полигона до 1 кп (мин)': time_from_first_kp_to_polygon,
#         'Дистанция от последней КП до полигона (км)': length_from_last_kp_to_polygon,
#         'Время движения от последней КП до полигона (мин)': time_from_last_kp_to_polygon,
#         'Общее время движения (мин)': trail_time + time_from_last_kp_to_polygon,
#         'Общая длина маршрута (км)': trail_length + length_from_last_kp_to_polygon,
#         'Общий объём загрузки машины (м3)': trail_weight
#     }

#     return copy_routes, trails
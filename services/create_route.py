from services.travel_length import shortest_travel_length, shortest_travel_length_iter
import pandas as pd

# Функция для расчёта маршрутов с учетом времени загрузки и выгрузки
def calculate_routes_iterrows(kp_cars_data, car, containers_data, G, lot, main_point):
    routes = []

    # Получаем данные о транспортном средстве
    car_lable = car[0] # Марка ТС
    car_code = car[6] # Код ТС
    # car_containers_type = car[1] # Виды контейнеров
    max_capacity = car[2] # Максимальный объём вместимости, м3
    max_working_time = car[4] # Норматив времени работы 1 ТС в сутки, час
    unload_time = car[5] # Время разгрузки, мин
    speed_road_kmh = car[3] # Средняя скорость движения, км/ч
    speed_city_kmh = car[7] # Средняя скорость движения в городе, км/ч
    
    # Для каждой контейнерной площадки
    iterrows = kp_cars_data.iterrows()
    # iterrows = kp_cars_data.itertuples()
    # print('iterrows: ', iterrows)
    _, next_row = next(iterrows)
    # print('next_row: ', next_row)
    
    # for _, start_row in iterrows:
    for _, start_row in iterrows:
        
        start_coords = (start_row['latitude_dd'], start_row['longitude_dd'])
        container_type = next_row['Вид контейнера']
        container_type = container_type.replace('.', ',')
        container_sum = next_row['Объем суточный']
        # print('start container_type: ', container_type)
        container_count = next_row['Количество контейнеров']
                
        # Получаем время загрузки для конкретного типа контейнера
        load_time = containers_data[containers_data['Вид контейнера'] == container_type]['Время загрузки,сек'].values[0]
        load_time_minutes = load_time * container_count / 60  # Общее время на загрузку всех контейнеров в минутах
               
        # Расчет времени на движение
        route_length_km = shortest_travel_length(next_row, G, start_coords)

        route_time = route_length_km / speed_city_kmh * 60

        start_distance_to_main_point = shortest_travel_length(next_row, G, main_point)
        last_distance_to_main_point = shortest_travel_length(start_row, G, main_point)

        # Составляем маршрут
        # total_time = load_time_minutes + travel_time
        routes.append({
            'Марка ТС': car_lable,
            'Начальная площадка': next_row['КП'],
            'Адрес начальной площадки': next_row['Адрес дома, здания'],
            'Расстояние начальной КП от точки старта': start_distance_to_main_point,
            'Конечная площадка': start_row['КП'],
            'Адрес конечной площадки': start_row['Адрес дома, здания'],
            'Расстояние конечной КП до полигона': last_distance_to_main_point,
            'Расстояние движения (км)': route_length_km,
            'Время движения (мин)': route_time,
            'Время загрузки (мин)': load_time_minutes,
            'Количество контейнеров': container_count,
            'Тип контейнеров': container_type,
            'Общий объём контейнеров': container_sum
        })

        next_row = start_row
    
    # Преобразуем результаты в DataFrame для удобного просмотра и сохраняем
    file_name = 'routes_'+ str(lot) +'.xlsx'
    routes_df = pd.DataFrame(routes)
    routes_df.to_excel(file_name, index=False)

    return routes_df


    # Функция для расчёта маршрутов с учетом времени загрузки и выгрузки
def calculate_routes_itertuples(kp_cars_data, car, containers_data, G, lot, main_point):
    routes = []



    # Получаем данные о транспортном средстве
    car_lable = car[0] # Марка ТС
    car_code = car[6] # Код ТС
    # car_containers_type = car[1] # Виды контейнеров
    max_capacity = car[2] # Максимальный объём вместимости, м3
    max_working_time = car[4] # Норматив времени работы 1 ТС в сутки, час
    unload_time = car[5] # Время разгрузки, мин
    speed_road_kmh = car[3] # Средняя скорость движения, км/ч
    speed_city_kmh = car[7] # Средняя скорость движения в городе, км/ч
    
    # Для каждой контейнерной площадки
    iterrows = kp_cars_data.itertuples()
    # print('iterrows: ', iterrows)
    next_row = next(iterrows)
    # print('next_row: ', next_row)
    # Составляем список столбцов из файла с кп
    next_kp_number = next_row[1] # № п\п	
    next_kp_comment = next_row[2] # коммент	
    next_kp_name = next_row[3] # КП	
    next_kp_latitude = next_row[4] # Координаты площадки (широта)	
    next_kp_longitude = next_row[5] # Координаты площадки (долгота)	
    next_kp_state = next_row[6] # Район обслуживания	
    next_kp_address = next_row[7] # Адрес дома, здания	
    next_kp_type = next_row[8] # Вид контейнера	
    next_kp_amount = next_row[9] # Количество контейнеров	
    next_kp_weight = next_row[10] # Объем суточный	
    next_kp_lot = next_row[11] # Лот

    # print(next_row)

    # print('next_kp_number: ', next_kp_number, 'next_kp_comment: ', next_kp_comment, 'next_kp_name: ', next_kp_name,
    #         'next_kp_latitude: ', next_kp_latitude, 'next_kp_longitude: ', next_kp_longitude, 'next_kp_state: ', next_kp_state,
    #         'next_kp_address: ', next_kp_address, 'next_kp_type: ', next_kp_type, 'next_kp_amount: ', next_kp_amount,
    #         'next_kp_weight: ', next_kp_weight )

    # for _, start_row in iterrows:
    for start_row in iterrows:
        
        start_coords = (start_row.latitude_dd, start_row.longitude_dd)
        container_type = next_kp_type
        container_type = container_type.replace('.', ',')
        container_sum = next_kp_weight
        # print('start container_type: ', container_type)
        container_count = next_kp_amount
                
        # Получаем время загрузки для конкретного типа контейнера
        load_time = containers_data[containers_data['Вид контейнера'] == container_type]['Время загрузки,сек'].values[0]
        load_time_minutes = load_time * container_count / 60  # Общее время на загрузку всех контейнеров в минутах
               
        # Расчет времени на движение
        route_length_km = shortest_travel_length_iter(next_row, G, start_coords)

        route_time = route_length_km / speed_city_kmh * 60

        start_distance_to_main_point = shortest_travel_length_iter(next_row, G, main_point)
        last_distance_to_main_point = shortest_travel_length_iter(start_row, G, main_point)

        # Составляем маршрут
        # total_time = load_time_minutes + travel_time
        routes.append({
            'Марка ТС': car_lable,
            'Начальная площадка': next_kp_name,
            'Адрес начальной площадки': next_kp_address,
            'Расстояние начальной КП от точки старта': start_distance_to_main_point,
            'Конечная площадка': start_row[3],
            'Адрес конечной площадки': start_row[7],
            'Расстояние конечной КП до полигона': last_distance_to_main_point,
            'Расстояние движения (км)': route_length_km,
            'Время движения (мин)': route_time,
            'Время загрузки (мин)': load_time_minutes,
            'Количество контейнеров': container_count,
            'Тип контейнеров': container_type,
            'Общий объём контейнеров': container_sum
        })

        next_row = start_row
    
    # Преобразуем результаты в DataFrame для удобного просмотра и сохраняем
    file_name = 'routes_'+ str(lot) +'.xlsx'
    routes_df = pd.DataFrame(routes)
    routes_df.to_excel(file_name, index=False)

    return routes_df
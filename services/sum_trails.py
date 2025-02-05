import pandas as pd

def sum_trails(file_path, working_time, lot, car_type, logging):
    trails_data = pd.read_excel(file_path)

    copy_trails_data = trails_data.copy()
    copy_trails_data = copy_trails_data[copy_trails_data['Лот'] == lot]
    copy_trails_data = copy_trails_data[copy_trails_data['Тип машины'] == car_type]

    trails = []

    while not copy_trails_data.shape[0] < 1:
        print('copy_trails_data.shape[0]: ', copy_trails_data.shape[0])
        iterrows = copy_trails_data.itertuples(index = True)

        current_row = next(iterrows)
        print('current_row = next(iterrows) INDEX: ', current_row.Index)

        # for current_row in iterrows:

        # print('current_row: ', current_row)

        trail_kp = current_row[1] # 'ID маршрута'
        trail_lot = current_row[2] # 'Лот'
        trail_state = current_row[3] # 'Название района'
        trail_route = current_row[4] # 'Состав маршрута'
        trail_type = current_row[5] # 'Тип контейнера'
        trail_car_type = current_row[6] # 'Тип машины'
        trail_car_id = current_row[7] # 'id машины'
        trail_kp_amount = current_row[8] # 'Количество КП'
        trail_container_amount = current_row[9] # 'Количество контейнеров'
        trail_weight = current_row[10] # 'Масса кг'
        trail_m = current_row[11] # 'Общий объём загрузки машины (м3)'
        trail_polygon = current_row[12] # 'Дистанция от полигона до 1 кп (км)'
        trail_around_kps = current_row[13] # 'Дистанция между КП (км)'
        trail_kp_to_polygon = current_row[14] # 'Дистанция от последней КП до полигона (км)'
        trail_speed = current_row[15] # 'Средняя скорость машины (км/ч)'
        trail_unload_min = current_row[16] # 'Время разгрузки (мин)'
        trail_load_hour = current_row[17] # 'Общее время погрузки (час)'
        trail_unload_hour = current_row[18] # 'Время разгрузки (час)'
        trail_drive_time = current_row[19] # 'Время в движении (час)'
        trail_time_hour = current_row[20] # 'Общее время прохождения маршрута (час)'
        trail_work_time = current_row[21] # 'Время стационарной работы (мин)'
        trail_distance = current_row[22] # 'Длина маршрута (км)'
        trail_time_min = current_row[23] # 'Общее время маршрута (мин)'

        # print('trail_time_min: ', trail_time_min, (float(working_time) * 0.80), (trail_time_min < (float(working_time) * 0.80)))
        if trail_time_min < (float(working_time) * 0.80):
            for next_row in iterrows:
                
                if next_row != current_row:
                    # print('This one!!!!')
                    print('next_row INDEX: ', next_row.Index)

                    sum_trail_time_min = trail_time_min + next_row[23]
                    if sum_trail_time_min < float(working_time):
                        # print("if sum_trail_time_min < float(working_time):")
                        trail = {
                            'ID маршрута': '',
                            'Лот': lot,
                            'Название района': trail_state,
                            'Состав маршрута': trail_route + next_row[4],
                            'Тип контейнера': trail_type,
                            'Тип машины': trail_car_type,
                            'id машины': trail_car_id,
                            'Количество КП': trail_kp_amount + next_row[8],
                            'Количество контейнеров': trail_container_amount + next_row[9],
                            'Масса кг': trail_weight + next_row[10],
                            'Общий объём загрузки машины (м3)': trail_m + next_row[11],
                            'Дистанция от полигона до 1 кп (км)': trail_polygon + next_row[12],
                            'Дистанция между КП (км)': trail_around_kps + next_row[13],
                            'Дистанция от последней КП до полигона (км)': trail_kp_to_polygon + next_row[14],
                            'Средняя скорость машины (км/ч)': trail_speed,
                            'Время разгрузки (мин)': trail_unload_min + next_row[16],
                            'Общее время погрузки (час)': trail_load_hour + next_row[17],
                            'Время разгрузки (час)': trail_unload_hour + next_row[18],
                            'Время в движении (час)': trail_drive_time + next_row[19],
                            'Общее время прохождения маршрута (час)': trail_time_hour + next_row[20],
                            'Время стационарной работы (мин)': trail_work_time + next_row[21],
                            'Длина маршрута (км)': trail_distance + next_row[22],
                            'Общее время маршрута (мин)': sum_trail_time_min
                        }
                        trails.append(trail)
                        copy_trails_data.drop(current_row.Index, inplace=True)
                        copy_trails_data.drop(next_row.Index, inplace=True)

                        iterrows = copy_trails_data.itertuples(index = True)
        else:
            trails.append(current_row)
            copy_trails_data.drop(current_row.Index, inplace=True)

            # iterrows = copy_trails_data.itertuples(index = True)
            
    print('Optimized trails: ', trails)
    output_file = f"results/result_optimize.xlsx"
    try:
        trails_data = pd.read_excel(output_file)
        all_trails_df = pd.DataFrame(trails)

        df = pd.concat([trails_data, all_trails_df], ignore_index=True)
        df.to_excel(output_file, index=False)

    except:
        all_trails_df = pd.DataFrame(trails)
        all_trails_df.to_excel(output_file, index=False)
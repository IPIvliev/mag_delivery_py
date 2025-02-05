import pandas as pd

def load_data(file_path):
    df = pd.read_excel(file_path)
    return df

def merge_routes(df, working_time):
    grouped = df.groupby(['Тип машины', 'Лот'])  # Группируем по типу машины и лоту
    merged_routes = []
    
    for (machine_type, lot), group in grouped:
        group = group.sort_values(by=['Общее время маршрута (мин)'], ascending=False)
        used_indices = set()
        
        while True:
            available_routes = [row for idx, row in group.iterrows() if idx not in used_indices]
            if not available_routes:
                break
            
            selected_routes = []
            total_time = 0
            
            for route in available_routes:
                if total_time + route['Общее время маршрута (мин)'] <= working_time:
                    selected_routes.append(route)
                    total_time += route['Общее время маршрута (мин)']
                if total_time >= (working_time - 30):  # Если время маршрута близко working_time, выходим. Установлен лимит 30 минут
                    break
            
            if not selected_routes:
                break
            
            for route in selected_routes:
                used_indices.add(route.name)
            
            merged_routes.append(merge_rows(selected_routes))
            # print(f"Объединено {len(selected_routes)} маршрутов для машины {machine_type}, суммарное время: {total_time} минут")
    
    return pd.DataFrame(merged_routes)

def merge_rows(rows):
    merged = rows[0].copy()
    merged['ID маршрута'] = ''
    merged['Лот'] = ' | '.join(set(str(row['Лот']) for row in rows))
    merged['Состав маршрута'] = ' | '.join(row['Состав маршрута'] for row in rows)
    merged['Тип контейнера'] = ' | '.join(str(row['Тип контейнера']) for row in rows)
    
    sum_columns = ['Количество КП', 'Количество контейнеров', 'Масса кг', 'Общий объём загрузки машины (м3)',
                   'Дистанция от полигона до 1 кп (км)', 'Дистанция между КП (км)', 'Дистанция от последней КП до полигона (км)',
                   'Время разгрузки (мин)', 'Общее время погрузки (час)', 'Время разгрузки (час)', 'Время в движении (час)',
                   'Общее время прохождения маршрута (час)', 'Время стационарной работы (мин)', 'Длина маршрута (км)',
                   'Общее время маршрута (мин)']
    
    for col in sum_columns:
        merged[col] = sum(row[col] for row in rows)
    
    return merged

def save_to_excel(df, output_file):
    df.to_excel(output_file, index=False)

def merge(input_file, output_file, working_time, logging):
    
    df = load_data(input_file)
    merged_df = merge_routes(df, working_time)
    save_to_excel(merged_df, output_file)
    logging.warning("Маршрутные листы успешно оптимизированы и сохранены в файл!")
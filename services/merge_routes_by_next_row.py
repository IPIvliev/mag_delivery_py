import pandas as pd
from itertools import combinations

def load_data(file_path):
    df = pd.read_excel(file_path)
    return df

def group_and_merge_routes(df, working_time):
    grouped = df.groupby(['Лот', 'Тип машины'])
    merged_routes = []
    
    for _, group in grouped:
        # group = group.sort_values(by=['Общее время маршрута (мин)'])
        used_indices = set()
        
        for i, row in group.iterrows():
            if i in used_indices:
                continue
            
            merged_group = [row]
            total_time = row['Общее время маршрута (мин)']
            
            for j, other_row in group.iterrows():
                if j in used_indices or j == i:
                    continue
                
                if total_time + other_row['Общее время маршрута (мин)'] <= working_time:
                    merged_group.append(other_row)
                    total_time += other_row['Общее время маршрута (мин)']
                    used_indices.add(j)
                else:
                    break
            
            used_indices.add(i)
            merged_routes.append(merge_rows(merged_group))
    
    return pd.DataFrame(merged_routes)

def merge_rows(rows):
    merged = rows[0].copy()
    merged['ID маршрута'] = ''
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
    merged_df = group_and_merge_routes(df, working_time)
    save_to_excel(merged_df, output_file)
    logging.warning("Файл успешно сохранен!")
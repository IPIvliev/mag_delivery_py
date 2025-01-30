import folium
import osmnx as ox

def plot_route_on_map(G, route, output_file="route_map.html"):
    """
    Визуализирует маршрут на интерактивной карте с использованием folium.
    :param G: Граф дорожной сети.
    :param route: Список узлов маршрута.
    :param output_file: Имя файла для сохранения карты.
    """
    # Получаем данные о координатах для узлов графа
    nodes_gdf = ox.graph_to_gdfs(G, nodes=True, edges=False)
    
    # Проверяем, что узлы есть в графе
    if nodes_gdf.empty:
        raise ValueError("Не удалось извлечь узлы из графа.")
    
    # Начальные координаты для карты — это первая вершина маршрута
    first_node = nodes_gdf.loc[route[0]]  # Здесь мы точно знаем, что route[0] — это индекс узла
    map_center = [first_node['y'], first_node['x']]
    
    # Создание карты
    route_map = folium.Map(location=map_center, zoom_start=13)
    
    # Преобразование маршрута в координаты
    route_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in route]
    
    # Добавление маршрута на карту
    folium.PolyLine(route_coords, color="blue", weight=5, opacity=0.8).add_to(route_map)
    
    for node in route:
        node_data = nodes_gdf.loc[node]
        folium.Marker(
            location=[node_data['y'], node_data['x']], 
            popup=f"Node {node}",  # Можно добавить информацию о узле, например, ID
            icon=folium.Icon(color="blue")
        ).add_to(route_map)

    # Добавление точек начала и конца
    folium.Marker(route_coords[0], popup="Start", icon=folium.Icon(color="green")).add_to(route_map)
    folium.Marker(route_coords[-1], popup="End", icon=folium.Icon(color="red")).add_to(route_map)
    
    # Сохранение карты
    route_map.save(output_file)
    print(f"Карта маршрута сохранена в {output_file}")

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
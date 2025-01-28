import osmnx as ox
import networkx as nx

def shortest_travel_length(row, G, start_point):
    # Поиск ближайших узлов графа для начальной и конечной точки
    origin_node = ox.distance.nearest_nodes(G, X=start_point[1], Y=start_point[0])
    destination_node = ox.distance.nearest_nodes(G, X=row['longitude_dd'], Y=row['latitude_dd'])

    # Вычисление длины маршрута в метрах
    route_length_meters = nx.shortest_path_length(G, origin_node, destination_node, weight="length")

    # Перевод длины в километры
    route_length_km = route_length_meters / 1000

    if float(route_length_km) == 0.0:
        route_length_km = 0.1

    print(start_point[0], start_point[1], row['latitude_dd'], row['longitude_dd'], row['Адрес дома, здания'], origin_node, destination_node, route_length_meters, route_length_km)

    return route_length_km

def shortest_travel_length_iter(row, G, start_point):
    # Поиск ближайших узлов графа для начальной и конечной точки
    origin_node = ox.distance.nearest_nodes(G, X=start_point[1], Y=start_point[0])
    destination_node = ox.distance.nearest_nodes(G, X=row.longitude_dd, Y=row.latitude_dd)

    # Вычисление длины маршрута в метрах
    route_length_meters = nx.shortest_path_length(G, origin_node, destination_node, weight="length")

    # Перевод длины в километры
    route_length_km = route_length_meters / 1000

    if float(route_length_km) == 0.0:
        route_length_km = 0.1

    print(start_point[0], start_point[1], row.latitude_dd, row.longitude_dd, row[7], origin_node, destination_node, route_length_meters, route_length_km)

    return route_length_km
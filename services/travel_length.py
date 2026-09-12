import logging as default_logging

import osmnx as ox
import networkx as nx


def prepare_nearest_nodes(G, coordinates):
    """Один пакетный поиск для координат текущего расчёта на неизменяемом графе."""
    points = list(dict.fromkeys((float(lat), float(lon)) for lat, lon in coordinates))
    if points:
        nodes = ox.distance.nearest_nodes(
            G, X=[point[1] for point in points], Y=[point[0] for point in points])
        lookup = {point: int(node) for point, node in zip(points, nodes)}
    else:
        lookup = {}
    # Данные принадлежат только этому объекту графа и не попадают в GraphML.
    G._route_node_lookup = lookup
    return len(lookup)


def _nearest_node(G, point):
    key = (float(point[0]), float(point[1]))
    lookup = getattr(G, '_route_node_lookup', {})
    if key in lookup:
        return lookup[key]
    # Совместимость с отдельными вызовами функций без подготовки полного расчёта.
    return ox.distance.nearest_nodes(G, X=key[1], Y=key[0])


def _route_length(G, start_point, end_point, distance, logger):
    origin_node = _nearest_node(G, start_point)
    destination_node = _nearest_node(G, end_point)
    try:
        return nx.shortest_path_length(G, origin_node, destination_node, weight="length") / 1000
    except nx.NetworkXNoPath:
        logger.warning(
            f"Нет дорожного пути от {start_point} до {end_point} "
            f"(узлы {origin_node} -> {destination_node}). "
            f"Использовано расстояние по умолчанию: {distance / 1000:g} км."
        )
        return distance / 1000


def shortest_travel_length_iter(row, G, start_point, distance):
    end_point = (row.latitude_dd, row.longitude_dd)
    return _route_length(G, start_point, end_point, distance, default_logging)


def shortest_travel_length_to_polygon_iter(
        row, G, start_point, distance, logging, text="", *, reverse=False):
    """По умолчанию полигон -> КП; reverse=True задаёт КП -> полигон."""
    platform_point = (row.latitude_dd, row.longitude_dd)
    origin, destination = (platform_point, start_point) if reverse else (start_point, platform_point)
    route_length_km = _route_length(G, origin, destination, distance, logging)
    direction = "КП -> полигон" if reverse else "полигон -> КП"
    logging.info(
        f"КПП: {row[3]} ({row.latitude_dd}, {row.longitude_dd}). "
        f"{text}. {direction}. Дистанция составила {route_length_km * 1000} м"
    )
    return route_length_km

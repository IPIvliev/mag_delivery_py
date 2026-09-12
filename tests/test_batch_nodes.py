import unittest
from unittest.mock import Mock, patch

import networkx as nx
import osmnx as ox
import pandas as pd

from services.travel_length import prepare_nearest_nodes, shortest_travel_length_to_polygon_iter
from services.calculate_trails import calculate_trail_for_single, calculate_trail_for_trip, calculate_trail_for_kgm
from test_routing import platforms, road_graph, POLYGON


class BatchNearestNodeTests(unittest.TestCase):
    def setUp(self):
        self.graph = road_graph()
        self.frame = platforms()
        self.coordinates = [POLYGON] + list(zip(self.frame.latitude_dd, self.frame.longitude_dd))
        self.reference = pd.DataFrame({'Вид контейнера': ['1', 'КГМ'], 'Время загрузки,сек': [60, 60]})

    def test_batch_returns_same_nodes_as_individual_lookups(self):
        expected = {point: ox.distance.nearest_nodes(self.graph, X=point[1], Y=point[0])
                    for point in self.coordinates}
        with patch('services.travel_length.ox.distance.nearest_nodes', wraps=ox.distance.nearest_nodes) as nearest:
            count = prepare_nearest_nodes(self.graph, self.coordinates * 2)
            self.assertEqual(count, 3)
            nearest.assert_called_once()
        self.assertEqual(self.graph._route_node_lookup, expected)

    def test_all_route_algorithms_produce_exactly_same_output(self):
        car = ('Машина', '1', 2, 60, 12, 1, 1, 60)
        for function in [calculate_trail_for_single, calculate_trail_for_trip, calculate_trail_for_kgm]:
            with self.subTest(function=function.__name__):
                graph = road_graph()
                args = (self.frame, self.reference, 720, car, 1, graph, POLYGON, 93, 24000, Mock())
                old_remaining, old_routes = function(*args)
                prepare_nearest_nodes(graph, self.coordinates)
                with patch('services.travel_length.ox.distance.nearest_nodes', side_effect=AssertionError('Unexpected repeated node lookup')):
                    new_remaining, new_routes = function(*args)
                pd.testing.assert_frame_equal(old_remaining, new_remaining, check_exact=True)
                self.assertEqual(old_routes, new_routes)

    def test_lookup_belongs_to_its_graph(self):
        second_graph = nx.relabel_nodes(self.graph, {1: 101, 2: 102, 3: 103})
        prepare_nearest_nodes(self.graph, self.coordinates)
        prepare_nearest_nodes(second_graph, self.coordinates)
        self.assertEqual(self.graph._route_node_lookup[POLYGON], 1)
        self.assertEqual(second_graph._route_node_lookup[POLYGON], 101)

    def test_unknown_coordinate_still_works_for_standalone_calls(self):
        prepare_nearest_nodes(self.graph, [POLYGON])
        row = next(self.frame.itertuples())
        with patch('services.travel_length.ox.distance.nearest_nodes', wraps=ox.distance.nearest_nodes) as nearest:
            length = shortest_travel_length_to_polygon_iter(row, self.graph, POLYGON, 24000, Mock())
        nearest.assert_called_once()
        self.assertEqual(length, 0.6)

    def test_repeated_distances_still_use_current_edge_lengths(self):
        prepare_nearest_nodes(self.graph, self.coordinates)
        row = next(self.frame.itertuples())
        before = shortest_travel_length_to_polygon_iter(row, self.graph, POLYGON, 24000, Mock())
        self.graph[1][2][0]['length'] = 700
        after = shortest_travel_length_to_polygon_iter(row, self.graph, POLYGON, 24000, Mock())
        self.assertEqual(before, 0.6)
        self.assertEqual(after, 0.7)

    def test_unreachable_route_keeps_fallback_and_warning(self):
        prepare_nearest_nodes(self.graph, self.coordinates)
        self.graph.remove_edges_from(list(self.graph.out_edges(1, keys=True)))
        logger = Mock()
        length = shortest_travel_length_to_polygon_iter(next(self.frame.itertuples()), self.graph, POLYGON, 24000, logger)
        self.assertEqual(length, 24)
        logger.warning.assert_called_once()


if __name__ == '__main__':
    unittest.main()

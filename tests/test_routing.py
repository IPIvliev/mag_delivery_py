import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import networkx as nx
import pandas as pd
from PyQt5 import QtWidgets

import main
from app import MainWindow
from services.calculate_trails import (
    calculate_trail_for_single, calculate_trail_for_trip, calculate_trail_for_kgm,
)
from services.travel_length import (
    shortest_travel_length_iter, shortest_travel_length_to_polygon_iter,
)


POLYGON = (56.32, 43.56)
COLUMNS = [
    '№ п\\п', 'коммент', 'КП', 'Координаты площадки (широта)',
    'Координаты площадки (долгота)', 'Район обслуживания', 'Адрес дома, здания',
    'Вид контейнера', 'Количество контейнеров', 'Объем суточный ТКО',
    'Лот', 'Объем суточный КГМ',
]


def platforms():
    frame = pd.DataFrame([
        [1, '', 'A', 56.32, 43.57, 'Район', 'Адрес A', '1', 1, 1, 1, 1],
        [2, '', 'B', 56.32, 43.58, 'Район', 'Адрес B', '1', 1, 1, 1, 1],
    ], columns=COLUMNS)
    return main.load_convert_coordinates(frame, 1)


def road_graph():
    graph = nx.MultiDiGraph(crs='EPSG:4326')
    for number, longitude in [(1, 43.56), (2, 43.57), (3, 43.58)]:
        graph.add_node(number, y=56.32, x=longitude)
    for start, end, length in [(1, 2, 600), (2, 1, 900), (2, 3, 400),
                               (3, 2, 1400), (3, 1, 1300), (1, 3, 1800)]:
        graph.add_edge(start, end, length=length)
    return graph


class AreaValidationTests(unittest.TestCase):
    def test_wrong_region_stops_before_map_download_or_removing_reports(self):
        with patch('main.ox.graph_from_point') as download, patch('main.os.remove') as remove:
            with self.assertRaisesRegex(ValueError, 'Ошибка заголовков Excel'):
                main.main(platforms(), pd.DataFrame(), (53.231607, 45.20543),
                          pd.DataFrame(), 720, 20000, 0.93, 24000, Mock(), True)
            download.assert_not_called()
            remove.assert_not_called()

    def test_matching_region_is_accepted(self):
        main.validate_route_area(platforms(), POLYGON, 20000)

    def test_point_outside_small_map_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'За пределами области карты'):
            main.validate_route_area(platforms(), POLYGON, 500)

    def test_invalid_coordinates_are_rejected(self):
        frame = platforms()
        frame.loc[0, 'Координаты площадки (долгота)'] = float('nan')
        with self.assertRaisesRegex(ValueError, 'строк с ошибками — 1'):
            main.validate_route_area(frame, POLYGON, 20000, Mock())


class TravelLengthTests(unittest.TestCase):
    def setUp(self):
        self.graph = road_graph()
        self.row = next(platforms().itertuples())
        self.logger = Mock()

    def test_short_route_keeps_real_length_and_return_direction(self):
        outbound = shortest_travel_length_to_polygon_iter(
            self.row, self.graph, POLYGON, 24000, self.logger)
        inbound = shortest_travel_length_to_polygon_iter(
            self.row, self.graph, POLYGON, 24000, self.logger, reverse=True)
        self.assertAlmostEqual(outbound, 0.6)
        self.assertAlmostEqual(inbound, 0.9)

    def test_short_inter_platform_distance_is_not_rounded_up(self):
        self.graph[1][2][0]['length'] = 150
        self.assertAlmostEqual(shortest_travel_length_iter(
            self.row, self.graph, POLYGON, 24000), 0.15)

    def test_unreachable_route_uses_fallback_with_warning(self):
        self.graph.remove_edges_from(list(self.graph.out_edges(1, keys=True)))
        length = shortest_travel_length_to_polygon_iter(
            self.row, self.graph, POLYGON, 24000, self.logger)
        self.assertEqual(length, 24)
        self.logger.warning.assert_called_once()

    def test_unexpected_failure_is_not_hidden_as_default_distance(self):
        with patch('services.travel_length.nx.shortest_path_length', side_effect=RuntimeError('broken')):
            with self.assertRaisesRegex(RuntimeError, 'broken'):
                shortest_travel_length_to_polygon_iter(
                    self.row, self.graph, POLYGON, 24000, self.logger)


class RouteCalculationTests(unittest.TestCase):
    def setUp(self):
        self.graph = road_graph()
        self.frame = platforms()
        self.containers = pd.DataFrame({
            'Вид контейнера': ['1', 'КГМ'], 'Время загрузки,сек': [60, 60],
        })
        self.logger = Mock()

    def calculate(self, function, capacity=2):
        car = ('Машина', '1', capacity, 60, 12, 1, 1, 60)
        return function(self.frame, self.containers, 720, car, 1,
                        self.graph, POLYGON, 93, 24000, self.logger)

    def test_single_container_includes_different_return_distance(self):
        remaining, trails = self.calculate(calculate_trail_for_single)
        self.assertEqual(len(remaining), 1)
        self.assertAlmostEqual(trails[0]['Длина маршрута (км)'], 1.5)
        self.assertAlmostEqual(trails[0]['Общее время маршрута (мин)'], 3.5)

    def test_multi_stop_routes_use_forward_legs_and_actual_return(self):
        for function in [calculate_trail_for_trip, calculate_trail_for_kgm]:
            with self.subTest(function=function.__name__):
                remaining, trails = self.calculate(function)
                self.assertTrue(remaining.empty)
                trail = trails[0]
                self.assertAlmostEqual(trail['Дистанция между КП (км)'], 0.4)
                self.assertAlmostEqual(trail['Дистанция от последней КП до полигона (км)'], 1.3)
                self.assertAlmostEqual(trail['Длина маршрута (км)'], 2.3)
                self.assertAlmostEqual(trail['Общее время маршрута (мин)'], 5.3)

    def test_rejected_stop_does_not_change_return_or_repeat_first_stop(self):
        for function in [calculate_trail_for_trip, calculate_trail_for_kgm]:
            with self.subTest(function=function.__name__):
                remaining, trails = self.calculate(function, capacity=1)
                self.assertEqual(list(remaining['КП']), ['B'])
                self.assertAlmostEqual(trails[0]['Длина маршрута (км)'], 1.5)
                self.assertAlmostEqual(trails[0]['Дистанция от последней КП до полигона (км)'], 0.9)


class CalculationWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_can_retry_after_background_failure_and_run_again_after_success(self):
        with patch.object(MainWindow, 'init_logger'), patch.object(MainWindow, 'show_error') as show_error:
            window = MainWindow()
            window.file_path = 'test.xlsx'
            with patch('app.pd.read_excel', return_value=pd.DataFrame()), \
                    patch('app.main.main', side_effect=[ValueError('wrong region'), None]) as calculate, \
                    patch('app.logging.exception'):
                self.assertEqual(window.latitude.text(), '53.231607')
                self.assertEqual(window.longitude.text(), '45.20543')
                for latitude, longitude, coordinates in [
                        ('53.231607', '45.20543', (53.231607, 45.20543)),
                        ('56,325792', '43,561192', (56.325792, 43.561192))]:
                    window.latitude.setText(latitude)
                    window.longitude.setText(longitude)
                    window.calculate_data()
                    window.calculation_thread.join(timeout=5)
                    self.assertFalse(window.calculation_thread.is_alive())
                    self.application.processEvents()
                    self.assertEqual(calculate.call_args.args[2], coordinates)
                    self.assertIsInstance(window.latitude, QtWidgets.QLineEdit)
                    self.assertIsInstance(window.longitude, QtWidgets.QLineEdit)
                    self.assertTrue(window.latitude.isEnabled())
                    self.assertTrue(window.longitude.isEnabled())
                    self.assertIsInstance(window.working_time, QtWidgets.QLineEdit)
                    self.assertTrue(window.btn_calculate.isEnabled())
                    self.assertTrue(window.btn_load.isEnabled())
                    self.assertEqual(window.btn_calculate.text(), 'Рассчитать')
                self.assertEqual(calculate.call_count, 2)
                show_error.assert_called_once_with('wrong region')
            window.close()


if __name__ == '__main__':
    unittest.main()

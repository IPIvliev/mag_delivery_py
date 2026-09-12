from decimal import Decimal
import unittest
from unittest.mock import Mock

import numpy as np
import pandas as pd

from main import filtered_by_cars
from services.container_types import normalize_container_type, parse_container_types, container_load_seconds
from services.calculate_trails import culculate_load_time, calculate_trail_for_trip
from services.input_validation import InputValidationError, validate_input_data
from test_routing import platforms, road_graph, POLYGON
from test_input_validation import cars


class ContainerNormalizationTests(unittest.TestCase):
    def test_numeric_representations_share_key(self):
        for value in [3, 3.0, np.int64(3), np.float64(3), '3', '3.000', ' 03,00 ', Decimal('3.000')]:
            with self.subTest(value=value):
                self.assertEqual(normalize_container_type(value), '3')
        self.assertEqual(normalize_container_type('0,7500'), '0.75')
        self.assertEqual(normalize_container_type(80), '80')
        self.assertEqual(normalize_container_type('1e-3'), '0.001')

    def test_distinct_volumes_are_not_rounded_into_one_type(self):
        self.assertNotEqual(normalize_container_type('1.0000000000001'), normalize_container_type('1.0000000000002'))
        self.assertNotEqual(normalize_container_type('0.75'), normalize_container_type('0.075'))

    def test_missing_and_nonfinite_values_do_not_become_types(self):
        for value in [None, pd.NA, float('nan'), float('inf'), '', '  ', 'NaN', '-Infinity']:
            with self.subTest(value=value):
                self.assertEqual(normalize_container_type(value), '')

    def test_vehicle_list_preserves_decimal_commas(self):
        self.assertEqual(parse_container_types(' 3,0; 3; 0,750; ;  КГМ '), {'3', '0.75', 'кгм'})
        self.assertEqual(parse_container_types(np.float64(3)), {'3'})
        self.assertEqual(parse_container_types(None), set())

    def test_vehicle_selection_normalizes_output_without_mutating_source(self):
        source = pd.DataFrame({'Вид контейнера': [1.0, 3.0, 8.0, 0.75, 0.750001]})
        original = source.copy(deep=True)
        selected = filtered_by_cars(source, '1; 3; 8; 0,75')
        self.assertEqual(list(selected.index), [0, 1, 2, 3])
        self.assertEqual(list(selected['Вид контейнера']), ['1', '3', '8', '0.75'])
        pd.testing.assert_frame_equal(source, original)

    def test_load_time_matches_numeric_and_named_types_without_mutation(self):
        reference = pd.DataFrame({'Вид контейнера': ['3,000', '  Бестарно ', ' кгм '],
                                  'Время загрузки,сек': [60, 120, 180]})
        original = reference.copy(deep=True)
        self.assertEqual(culculate_load_time(3.0, 2, reference), 2)
        self.assertEqual(culculate_load_time('БЕСТАРНО', 8, reference), 2)
        self.assertEqual(culculate_load_time('КГМ', 1, reference), 3)
        pd.testing.assert_frame_equal(reference, original)

    def test_conflicting_normalized_norms_fail_preflight_and_lookup(self):
        reference = pd.DataFrame({'Вид контейнера': [1.0, '1,00'], 'Время загрузки,сек': [60, 90]})
        logger = Mock()
        with self.assertRaises(InputValidationError):
            validate_input_data(platforms(), cars(), reference, POLYGON, 20000, logger)
        self.assertTrue(any('разные нормативы загрузки в строках 2 и 3' in call.args[0]
                            for call in logger.error.call_args_list))
        with self.assertRaisesRegex(ValueError, 'разные нормативы загрузки'):
            container_load_seconds('1', reference)

    def test_duplicate_equivalent_norms_with_same_time_are_allowed(self):
        reference = pd.DataFrame({'Вид контейнера': [1.0, '1,00'], 'Время загрузки,сек': [60, 60]})
        logger = Mock()
        self.assertEqual(len(validate_input_data(platforms(), cars(), reference, POLYGON, 20000, logger)), 2)
        self.assertEqual(container_load_seconds('1', reference), 60)

    def test_validation_selection_and_route_loading_use_same_keys(self):
        source = platforms()
        source['Вид контейнера'] = [1.0, '1,00']
        auto = cars()
        auto['Виды контейнеров'] = [' 1,000 ']
        reference = pd.DataFrame({'Вид контейнера': ['01.0'], 'Время загрузки,сек': [60]})
        prepared = validate_input_data(source, auto, reference, POLYGON, 20000, Mock())
        selected = filtered_by_cars(prepared, auto.iloc[0]['Виды контейнеров'])
        self.assertEqual(len(selected), 2)
        car = ('Машина', '1,000', 2, 60, 12, 1, 1, 60)
        remaining, trails = calculate_trail_for_trip(selected, reference, 720, car, 1,
                                                   road_graph(), POLYGON, 93, 24000, Mock())
        self.assertTrue(remaining.empty)
        self.assertEqual(trails[0]['Количество КП'], 2)
        self.assertAlmostEqual(trails[0]['Общее время погрузки (час)'], 2 / 60)
        self.assertAlmostEqual(trails[0]['Общее время маршрута (мин)'], 5.3)


if __name__ == '__main__':
    unittest.main()

import unittest
from unittest.mock import Mock, patch

import pandas as pd

import main
from services.input_validation import InputValidationError, validate_input_data, dm_to_dd
from test_routing import platforms, POLYGON


def cars():
    return pd.DataFrame({
        'Код ТС': [1], 'Марка ТС': ['Машина'],
        'Максимальный объём вместимости, м3': [20], 'Виды контейнеров': ['1; 3; 8'],
        'Норматив времени работы 1 ТС в сутки, час': [12], 'Время разгрузки, мин': [10],
        'Средняя скорость движения, км/ч': [40], 'Средняя скорость движения в городе, км/ч': [24],
    })


def containers():
    return pd.DataFrame({'Вид контейнера': ['1', '3', '8'], 'Время загрузки,сек': [60, 60, 60]})


class InputValidationTests(unittest.TestCase):
    def setUp(self):
        self.logger = Mock()
        self.kp = platforms().iloc[:, :12].copy()

    def validate(self, kp=None, auto=None, reference=None):
        return validate_input_data(self.kp if kp is None else kp,
                                   cars() if auto is None else auto,
                                   containers() if reference is None else reference,
                                   POLYGON, 20000, self.logger)

    def errors(self):
        return '\n'.join(call.args[0] for call in self.logger.error.call_args_list)

    def test_all_invalid_rows_and_multiple_reasons_are_logged(self):
        self.kp.loc[0, 'Координаты площадки (широта)'] = 'ошибка'
        self.kp.loc[0, 'Количество контейнеров'] = -1
        self.kp.loc[1, 'Координаты площадки (долгота)'] = float('nan')
        with self.assertRaisesRegex(InputValidationError, 'строк с ошибками — 2'):
            self.validate()
        messages = self.errors()
        self.assertIn('строка Excel 2 (КП A)', messages)
        self.assertIn('строка Excel 3 (КП B)', messages)
        self.assertIn('широта', messages)
        self.assertIn('долгота', messages)
        self.assertIn('Количество контейнеров', messages)
        self.assertEqual(self.logger.error.call_count, 2)

    def test_swapped_coordinates_are_reported_without_changing_data(self):
        self.kp.loc[0, ['Координаты площадки (широта)', 'Координаты площадки (долгота)']] = [43.57, 56.32]
        original = self.kp.copy(deep=True)
        with self.assertRaises(InputValidationError):
            self.validate()
        self.assertIn('вероятно, широта и долгота перепутаны', self.errors())
        pd.testing.assert_frame_equal(self.kp, original)

    def test_unlabelled_total_is_skipped_but_input_is_preserved(self):
        total = {column: None for column in self.kp.columns}
        total.update({'Количество контейнеров': 2, 'Объем суточный ТКО': 2})
        self.kp.loc[2] = total
        original = self.kp.copy(deep=True)
        result = self.validate()
        self.assertEqual(len(result), 2)
        self.assertIn('строка Excel 4: итоговая строка', self.logger.warning.call_args.args[0])
        pd.testing.assert_frame_equal(self.kp, original)

    def test_unidentified_bad_row_is_not_silently_treated_as_total(self):
        bad = {column: None for column in self.kp.columns}
        bad.update({'Количество контейнеров': 99, 'Объем суточный ТКО': 99})
        self.kp.loc[2] = bad
        with self.assertRaises(InputValidationError):
            self.validate()
        self.assertIn('строка Excel 4', self.errors())
        self.logger.warning.assert_not_called()

    def test_excel_row_numbers_do_not_shift_after_empty_row(self):
        blank = pd.DataFrame([{column: None for column in self.kp.columns}])
        frame = pd.concat([self.kp.iloc[:1], blank, self.kp.iloc[1:]], ignore_index=True)
        frame.loc[2, 'Лот'] = None
        with self.assertRaises(InputValidationError):
            self.validate(frame)
        self.assertIn('строка Excel 4 (КП B)', self.errors())
        self.assertIn('строка Excel 3: пустая строка', self.logger.warning.call_args.args[0])

    def test_float_container_matches_integer_type_in_vehicle_and_reference(self):
        self.kp.loc[0, 'Вид контейнера'] = 3.0
        original = self.kp.copy(deep=True)
        result = self.validate()
        self.assertEqual(len(result), 2)
        self.logger.error.assert_not_called()
        pd.testing.assert_frame_equal(self.kp, original)

    def test_missing_reference_and_invalid_auto_rows_are_both_logged(self):
        auto = cars()
        auto.loc[0, 'Средняя скорость движения, км/ч'] = 0
        reference = containers()
        reference.loc[0, 'Время загрузки,сек'] = 'abc'
        self.kp.loc[0, 'Вид контейнера'] = 'неизвестный'
        with self.assertRaises(InputValidationError):
            self.validate(auto=auto, reference=reference)
        self.assertIn('Лист «Авто», строка Excel 2', self.errors())
        self.assertIn('Лист «Виды контейнеров», строка Excel 2', self.errors())
        self.assertIn('Лист «КП», строка Excel 2', self.errors())
        self.assertIn('Не найден норматив загрузки', self.errors())

    def test_integer_reference_is_not_changed_by_float_loading_time(self):
        reference = pd.DataFrame({'Вид контейнера': [1, 3, 8], 'Время загрузки,сек': [18.5, 60, 60]})
        self.assertEqual(len(self.validate(reference=reference)), 2)

    def test_wrong_region_stops_before_network_and_report_changes(self):
        with patch('main.ox.graph_from_point') as download, patch('main.os.remove') as remove:
            with self.assertRaises(InputValidationError):
                main.main(self.kp, cars(), (53.231607, 45.20543), containers(),
                          720, 20000, 0.93, 24000, self.logger, True)
            download.assert_not_called()
            remove.assert_not_called()
        self.assertIn('строка Excel 2 (КП A)', self.errors())
        self.assertIn('строка Excel 3 (КП B)', self.errors())

    def test_header_errors_have_sheet_and_header_row(self):
        with self.assertRaises(InputValidationError):
            self.validate(self.kp.drop(columns=['Лот']))
        self.assertIn('Лист «КП», строка Excel 1', self.errors())
        self.assertIn('Лот', self.errors())

    def test_decimal_comma_and_degrees_minutes_are_supported(self):
        self.assertAlmostEqual(dm_to_dd('53,1890716'), 53.1890716)
        self.assertAlmostEqual(dm_to_dd('56.14.833'), 56 + 14.833 / 60)
        self.assertAlmostEqual(dm_to_dd('56,14,833'), 56 + 14.833 / 60)


if __name__ == '__main__':
    unittest.main()

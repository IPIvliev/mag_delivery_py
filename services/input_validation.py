"""Проверка строк Excel до загрузки дорожной сети и изменения отчётов."""
import logging
import math

import osmnx as ox
import pandas as pd
from services.container_types import normalize_container_type, parse_container_types

LATITUDE = 'Координаты площадки (широта)'
LONGITUDE = 'Координаты площадки (долгота)'
CONTAINER = 'Вид контейнера'
COUNT = 'Количество контейнеров'
VOLUME = 'Объем суточный ТКО'
AUTO_COLUMNS = [
    'Код ТС', 'Марка ТС', 'Максимальный объём вместимости, м3',
    'Виды контейнеров', 'Норматив времени работы 1 ТС в сутки, час',
    'Время разгрузки, мин', 'Средняя скорость движения, км/ч',
    'Средняя скорость движения в городе, км/ч',
]


class InputValidationError(ValueError):
    """Подробности уже записаны в журнал по строкам Excel."""


def dm_to_dd(value):
    text = str(value).strip().replace(',', '.')
    parts = text.split('.')
    if len(parts) == 3:
        degrees, minutes, fraction = parts
        minutes = float(minutes + '.' + fraction)
        if not 0 <= minutes < 60:
            raise ValueError('Минуты координаты должны быть от 0 до 60')
        degrees = int(degrees)
        return degrees + (-1 if text.startswith('-') else 1) * minutes / 60
    return float(text)


def _empty(value):
    return bool(pd.isna(value)) or (isinstance(value, str) and not value.strip())


def _number(value):
    if _empty(value):
        raise ValueError('пустое значение')
    number = float(value)
    if not math.isfinite(number):
        raise ValueError('не конечное число')
    return number


def _is_total(row, totals):
    identity = ['КП', LATITUDE, LONGITUDE, 'Район обслуживания',
                'Адрес дома, здания', CONTAINER, 'Лот']
    marker = str(row.get('КП', '')).strip().casefold() in ('итого', 'всего')
    if any(not _empty(row.get(column)) for column in identity if column != 'КП'):
        return False
    if marker:
        return True
    if not _empty(row.get('КП')) or not _empty(row.iloc[0]):
        return False
    # Без подписи считаем строку итоговой только при совпадении обеих сумм.
    try:
        return all(math.isclose(_number(row[column]), total, rel_tol=1e-7, abs_tol=1e-6)
                   for column, total in totals.items())
    except (ValueError, TypeError):
        return False


def _validate(kp_data, main_point, accuracy, logger, auto_data=None, containers_data=None):
    logger.info('Проверка входных данных перед расчётом.')
    errors = 0
    warnings = 0

    def error(sheet, row_number, reasons, name=None):
        nonlocal errors
        errors += 1
        label = f" (КП {name})" if name is not None and not _empty(name) else ''
        logger.error(f"Лист «{sheet}», строка Excel {row_number}{label}: " + '; '.join(reasons))

    # Сначала проверяем заголовки: при их отсутствии нельзя читать поля строк.
    volume_column = VOLUME if VOLUME in kp_data.columns else 'Объем суточный'
    required_kp = ['КП', LATITUDE, LONGITUDE, 'Район обслуживания', 'Адрес дома, здания',
                   CONTAINER, COUNT, volume_column, 'Лот', 'Объем суточный КГМ']
    sheets = [('КП', kp_data, required_kp)]
    if auto_data is not None:
        sheets.append(('Авто', auto_data, AUTO_COLUMNS))
    if containers_data is not None:
        sheets.append(('Виды контейнеров', containers_data, [CONTAINER, 'Время загрузки,сек']))
    for sheet, frame, required in sheets:
        missing = [column for column in required if column not in frame.columns]
        if missing:
            error(sheet, 1, ['Отсутствуют столбцы: ' + ', '.join(missing)])
    if errors:
        raise InputValidationError('Ошибка заголовков Excel. Подробности по листам — в журнале.')

    # Алгоритмы маршрутов используют позиции столбцов на листе КП.
    for position, column in enumerate(required_kp, start=2):
        if position >= len(kp_data.columns) or kp_data.columns[position] != column:
            error('КП', 1, [f'Столбец «{column}» должен быть на позиции {position + 1}'])
    if errors:
        raise InputValidationError('Неверный порядок столбцов листа КП. Подробности — в журнале.')

    if (len(main_point) != 2 or not all(math.isfinite(value) for value in main_point)
            or not -90 < main_point[0] < 90 or not -180 <= main_point[1] <= 180):
        logger.error('Параметры расчёта: некорректные координаты полигона.')
        raise InputValidationError('Некорректные координаты полигона.')
    if not math.isfinite(accuracy) or accuracy <= 0:
        logger.error('Параметры расчёта: размер области карты должен быть больше нуля.')
        raise InputValidationError('Размер области карты должен быть больше нуля.')
    west, south, east, north = ox.utils_geo.bbox_from_point(main_point, dist=accuracy)

    supported = set()
    if auto_data is not None:
        if auto_data.empty:
            error('Авто', 2, ['Нет данных об автомобилях'])
        for row_number, (_, row) in enumerate(auto_data.iterrows(), start=2):
            reasons = []
            for column in ['Марка ТС', 'Код ТС', 'Виды контейнеров']:
                if _empty(row[column]):
                    reasons.append(f'Не заполнено поле «{column}»')
            for column in AUTO_COLUMNS[2:]:
                if column == 'Виды контейнеров':
                    continue
                try:
                    value = _number(row[column])
                    if value < 0 or (value == 0 and column != 'Время разгрузки, мин'):
                        raise ValueError()
                except (ValueError, TypeError):
                    reasons.append(f'Недопустимое числовое значение «{column}»: {row[column]!r}')
            kinds = parse_container_types(row['Виды контейнеров'])
            supported.update(kinds)
            if not kinds and not _empty(row['Виды контейнеров']):
                reasons.append('Не указаны допустимые виды контейнеров')
            if reasons:
                error('Авто', row_number, reasons)

    reference = set()
    if containers_data is not None:
        reference = set(containers_data[CONTAINER].map(normalize_container_type)) - {''}
        reference_rows = {}
        if containers_data.empty:
            error('Виды контейнеров', 2, ['Нет нормативов загрузки контейнеров'])
        for row_number, (_, row) in enumerate(containers_data.iterrows(), start=2):
            reasons = []
            kind = normalize_container_type(row[CONTAINER])
            if not kind:
                reasons.append('Не заполнен или некорректен вид контейнера')
            try:
                load_time = _number(row['Время загрузки,сек'])
                if load_time < 0:
                    raise ValueError()
                if kind in reference_rows and reference_rows[kind][1] != load_time:
                    reasons.append(f"Для контейнера '{kind}' заданы разные нормативы загрузки в строках {reference_rows[kind][0]} и {row_number}")
                elif kind:
                    reference_rows.setdefault(kind, (row_number, load_time))
            except (ValueError, TypeError):
                reasons.append(f"Некорректное время загрузки: {row['Время загрузки,сек']!r}")
            if reasons:
                error('Виды контейнеров', row_number, reasons)

    actual = kp_data[kp_data['КП'].notna() & ~kp_data['КП'].astype(str).str.strip().str.casefold().isin(['итого', 'всего'])]
    totals = {column: pd.to_numeric(actual[column], errors='coerce').sum()
              for column in [COUNT, volume_column]}
    kept_positions = []
    outside_count = 0
    for position, (_, row) in enumerate(kp_data.iterrows()):
        row_number = position + 2
        if all(_empty(value) for value in row):
            warnings += 1
            logger.warning(f'Лист «КП», строка Excel {row_number}: пустая строка исключена из расчёта.')
            continue
        if _is_total(row, totals):
            warnings += 1
            logger.warning(f'Лист «КП», строка Excel {row_number}: итоговая строка, а не площадка; исключена из расчёта.')
            continue
        kept_positions.append(position)
        reasons = []
        for column in ['КП', 'Лот', 'Район обслуживания', 'Адрес дома, здания', CONTAINER]:
            if _empty(row[column]):
                reasons.append(f'Не заполнено поле «{column}»')
        coordinates = []
        for column, limit in [(LATITUDE, 90), (LONGITUDE, 180)]:
            try:
                coordinate = dm_to_dd(row[column])
                if not math.isfinite(coordinate) or not -limit <= coordinate <= limit:
                    raise ValueError()
                coordinates.append(coordinate)
            except (ValueError, TypeError):
                reasons.append(f'Пустые или некорректные координаты: «{column}» = {row[column]!r}')
        if len(coordinates) == 2:
            latitude, longitude = coordinates
            if not (south <= latitude <= north and west <= longitude <= east):
                outside_count += 1
                message = f'Координаты ({latitude}, {longitude}) за пределами области карты {accuracy / 1000:g} км вокруг полигона {main_point}'
                if south <= longitude <= north and west <= latitude <= east:
                    message += '; вероятно, широта и долгота перепутаны местами'
                reasons.append(message)
        for column in [COUNT, volume_column, 'Объем суточный КГМ']:
            if column == 'Объем суточный КГМ' and _empty(row[column]):
                continue
            try:
                value = _number(row[column])
                if value < 0 or (column == COUNT and (value == 0 or not value.is_integer())):
                    raise ValueError()
            except (ValueError, TypeError):
                reasons.append(f'Недопустимое значение «{column}»: {row[column]!r}')
        if not _empty(row[CONTAINER]):
            kind = normalize_container_type(row[CONTAINER])
            if not kind:
                reasons.append(f'Некорректный вид контейнера: {row[CONTAINER]!r}')
            if auto_data is not None and kind not in supported:
                reasons.append(f'Нет подходящей машины для вида контейнера: {row[CONTAINER]!r}')
            if containers_data is not None and kind not in reference:
                reasons.append(f'Не найден норматив загрузки вида контейнера: {row[CONTAINER]!r}')
        if reasons:
            error('КП', row_number, reasons, row['КП'])

    if not kept_positions:
        error('КП', 2, ['Нет строк контейнерных площадок для расчёта'])
    logger.info(f'Проверка завершена: строк КП — {len(kp_data)}, исключено — {warnings}, строк с ошибками во всех листах — {errors}.')
    if errors:
        area = f' За пределами области карты: {outside_count} из {len(kept_positions)} КП.' if outside_count else ''
        raise InputValidationError(
            f'Проверка Excel: строк с ошибками — {errors}.{area} '
            'Расчёт не начат. Номера строк и причины указаны в журнале.'
        )
    return kp_data.iloc[kept_positions].copy()


def validate_route_area(kp_data, main_point, accuracy, logger=None):
    return _validate(kp_data, main_point, accuracy, logger or logging)


def validate_input_data(kp_data, auto_data, containers_data, main_point, accuracy, logger):
    return _validate(kp_data, main_point, accuracy, logger, auto_data, containers_data)

"""Единые ключи типов контейнеров для проверки, подбора ТС и нормативов."""
from decimal import Decimal, InvalidOperation
import math

import pandas as pd


def normalize_container_type(value):
    """3, 3.0 и '3,00' -> '3'; '  БЕСТАРНО ' -> 'бестарно'."""
    if pd.isna(value):
        return ''
    text = str(value).strip().replace(',', '.')
    if not text:
        return ''
    try:
        number = Decimal(text)
    except InvalidOperation:
        return text.casefold()
    if not number.is_finite():
        return ''
    if number == 0:
        return '0'
    # Без округления через float: близкие, но разные объёмы сохраняются.
    result = format(number, 'f')
    return result.rstrip('0').rstrip('.') if '.' in result else result


def parse_container_types(value):
    """Список типов машины разделяется точкой с запятой, а не десятичной запятой."""
    if pd.isna(value):
        return set()
    return {kind for item in str(value).split(';')
            if (kind := normalize_container_type(item))}


def container_load_seconds(container_type, containers_data):
    kind = normalize_container_type(container_type)
    keys = containers_data['Вид контейнера'].map(normalize_container_type)
    matching = containers_data.loc[keys.eq(kind), 'Время загрузки,сек']
    if not kind or matching.empty:
        raise ValueError(f"Контейнер типа {kind!r} не найден")
    values = [float(value) for value in matching]
    if any(not math.isfinite(value) or value < 0 for value in values):
        raise ValueError(f"Некорректное время загрузки контейнера {kind!r}")
    if len(set(values)) > 1:
        raise ValueError(f"Для контейнера {kind!r} заданы разные нормативы загрузки")
    return values[0]

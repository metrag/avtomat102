"""Статистика тренировочной сессии.

Чистая логика без зависимостей от PyQt/SQLite.
"""

from datetime import datetime
from typing import Any


def _parse_timestamp(value: Any) -> datetime:
    """Преобразует значение timestamp в datetime.

    Поддерживает:
    - объекты datetime;
    - строки ISO 8601;
    - строки времени ``%H:%M:%S`` и ``%H:%M:%S.%f`` (привязываются к текущей дате).

    Args:
        value: Исходное значение timestamp.

    Returns:
        Объект datetime.

    Raises:
        ValueError: Если формат значения не поддерживается.
    """
    if isinstance(value, datetime):
        return value

    if not isinstance(value, str):
        raise ValueError(f"Unsupported timestamp type: {type(value)}")

    value = value.strip()

    # Полная ISO-строка, включая формат журнала SQLite.
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        pass

    # Только время (используется в GUI).
    for fmt in ("%H:%M:%S.%f", "%H:%M:%S"):
        try:
            parsed = datetime.strptime(value, fmt)
            return datetime.now().replace(
                hour=parsed.hour,
                minute=parsed.minute,
                second=parsed.second,
                microsecond=parsed.microsecond,
            )
        except ValueError:
            pass

    raise ValueError(f"Unsupported timestamp format: {value!r}")


def summarize(shots: list[dict[str, Any]]) -> dict[str, Any]:
    """Формирует сводку по списку выстрелов.

    Args:
        shots: Список выстрелов. Каждый элемент должен содержать
            ключ ``timestamp`` (datetime или строка) и ``hit`` (bool/int).

    Returns:
        Словарь со статистикой:

        - ``hits`` (int): количество попаданий;
        - ``misses`` (int): количество промахов;
        - ``total`` (int): общее количество выстрелов;
        - ``accuracy`` (float): точность в диапазоне ``0.0..1.0``;
        - ``accuracy_percent`` (float): точность в процентах ``0.0..100.0``;
        - ``avg_interval_sec`` (float): среднее время между выстрелами в секундах.
    """
    total = len(shots)
    if total == 0:
        return {
            "hits": 0,
            "misses": 0,
            "total": 0,
            "accuracy": 0.0,
            "accuracy_percent": 0.0,
            "avg_interval_sec": 0.0,
        }

    hits = sum(1 for shot in shots if shot.get("hit"))
    misses = total - hits
    accuracy = hits / total if total > 0 else 0.0

    timestamps = sorted(_parse_timestamp(shot["timestamp"]) for shot in shots)
    if len(timestamps) < 2:
        avg_interval = 0.0
    else:
        intervals = [
            (timestamps[i] - timestamps[i - 1]).total_seconds()
            for i in range(1, len(timestamps))
        ]
        avg_interval = sum(intervals) / len(intervals)

    return {
        "hits": hits,
        "misses": misses,
        "total": total,
        "accuracy": accuracy,
        "accuracy_percent": accuracy * 100.0,
        "avg_interval_sec": avg_interval,
    }

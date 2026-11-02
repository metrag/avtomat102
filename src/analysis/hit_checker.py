"""Чистая логика проверки попадания по контуру, многоугольнику и ограничивающей рамке."""

from typing import List, Sequence, Tuple

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None  # type: ignore[assignment]


def point_in_polygon(point: tuple[int, int], polygon: Sequence[tuple[int, int]]) -> bool:
    """Проверяет, находится ли точка внутри многоугольника.

    Используется алгоритм луча (ray casting) без внешних зависимостей.

    Args:
        point: Точка прицеливания в формате (x, y).
        polygon: Последовательность вершин многоугольника (x, y).

    Returns:
        True, если точка внутри многоугольника или на его границе,
        иначе False.

    Example:
        >>> point_in_polygon((5, 5), [(0, 0), (10, 0), (10, 10), (0, 10)])
        True
    """
    if not polygon:
        return False

    x, y = point
    inside = False
    n = len(polygon)

    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]

        # Проверка, лежит ли точка на отрезке.
        if _point_on_segment(point, (x1, y1), (x2, y2)):
            return True

        # Проверка пересечения луча, идущего вправо, со стороной многоугольника.
        if ((y1 > y) != (y2 > y)) and (
            x < (x2 - x1) * (y - y1) / (y2 - y1) + x1
        ):
            inside = not inside

    return inside


def _point_on_segment(
    point: tuple[int, int],
    segment_start: tuple[int, int],
    segment_end: tuple[int, int],
) -> bool:
    """Проверяет, лежит ли точка на отрезке между двумя вершинами."""
    px, py = point
    x1, y1 = segment_start
    x2, y2 = segment_end

    cross_product = (py - y1) * (x2 - x1) - (px - x1) * (y2 - y1)
    if cross_product != 0:
        return False

    dot_product = (px - x1) * (px - x2) + (py - y1) * (py - y2)
    if dot_product > 0:
        return False

    return (
        min(x1, x2) <= px <= max(x1, x2)
        and min(y1, y2) <= py <= max(y1, y2)
    )


def point_in_bbox(
    point: tuple[int, int],
    bbox: tuple[int, int, int, int],
) -> bool:
    """Проверяет, находится ли точка внутри ограничивающей рамки.

    Args:
        point: Точка (x, y).
        bbox: Рамка в формате (x_min, y_min, x_max, y_max).

    Returns:
        True, если точка внутри рамки или на её границе.

    Example:
        >>> point_in_bbox((5, 5), (0, 0, 10, 10))
        True
    """
    x, y = point
    x_min, y_min, x_max, y_max = bbox
    return x_min <= x <= x_max and y_min <= y <= y_max


def point_in_contour(point: Tuple[float, float], contour: List[Tuple[int, int]]) -> bool:
    """
    Проверяет, находится ли точка внутри контура.

    Args:
        point: (x, y) координаты прицела
        contour: Список точек контура [(x1, y1), (x2, y2), ...]

    Returns:
        True если точка внутри контура
    """
    if len(contour) < 3:
        return False

    # Если cv2 недоступен, используем point_in_polygon как fallback
    if cv2 is None:
        return point_in_polygon((int(point[0]), int(point[1])), contour)

    # Конвертируем в формат для cv2
    contour_array = np.array(contour, dtype=np.int32)
    result = cv2.pointPolygonTest(contour_array, point, measureDist=False)
    return result >= 0  # 0 = на границе, >0 = внутри


def check_hit(aim_point: Tuple[float, float], detections) -> bool:
    """
    Проверяет попадание по любой из детекций.

    Args:
        aim_point: Координаты прицела (x, y)
        detections: Список детекций с контурами

    Returns:
        True если прицел внутри хотя бы одного контура
    """
    for detection in detections:
        if point_in_contour(aim_point, detection.contour):
            return True
    return False

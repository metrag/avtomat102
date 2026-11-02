"""Тесты для модуля проверки попаданий."""

import pytest

from src.analysis.hit_checker import point_in_bbox, point_in_polygon


class TestPointInPolygon:
    """Тесты точки внутри многоугольника."""

    def test_point_inside_square(self):
        """Точка внутри квадрата — попадание."""
        square = [(0, 0), (10, 0), (10, 10), (0, 10)]
        assert point_in_polygon((5, 5), square) is True

    def test_point_outside_square(self):
        """Точка снаружи квадрата — промах."""
        square = [(0, 0), (10, 0), (10, 10), (0, 10)]
        assert point_in_polygon((15, 15), square) is False

    def test_point_on_edge(self):
        """Точка на границе считается попаданием."""
        square = [(0, 0), (10, 0), (10, 10), (0, 10)]
        assert point_in_polygon((10, 5), square) is True

    def test_empty_polygon(self):
        """Пустой многоугольник — всегда промах."""
        assert point_in_polygon((0, 0), []) is False

    def test_triangle(self):
        """Тест для треугольника."""
        triangle = [(0, 0), (10, 0), (5, 10)]
        assert point_in_polygon((5, 3), triangle) is True
        assert point_in_polygon((1, 5), triangle) is False


class TestPointInBbox:
    """Тесты точки внутри ограничивающей рамки."""

    def test_point_inside_bbox(self):
        """Точка внутри рамки — попадание."""
        assert point_in_bbox((5, 5), (0, 0, 10, 10)) is True

    def test_point_outside_bbox(self):
        """Точка снаружи рамки — промах."""
        assert point_in_bbox((15, 5), (0, 0, 10, 10)) is False

    def test_point_on_border(self):
        """Точка на границе рамки — попадание."""
        assert point_in_bbox((10, 5), (0, 0, 10, 10)) is True

"""Тесты для модуля проверки попаданий."""

import pytest

import numpy as np

from src.analysis.hit_checker import point_in_bbox, point_in_polygon, point_in_contour, check_hit
from src.detection.detector import Detection


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


def test_point_in_contour():
    """Тест проверки точки внутри контура."""
    contour = [(0, 0), (100, 0), (100, 100), (0, 100)]
    
    # Точка внутри
    assert point_in_contour((50, 50), contour) is True
    
    # Точка снаружи
    assert point_in_contour((150, 150), contour) is False
    
    # Точка на границе
    assert point_in_contour((0, 0), contour) is True


def test_check_hit():
    """Тест проверки попадания по детекциям."""
    detections = [
        Detection(
            bbox=np.array([100, 100, 200, 200]),
            contour=[(100, 100), (200, 100), (200, 200), (100, 200)],
            confidence=0.9,
            class_id=0
        )
    ]
    
    # Попадание
    assert check_hit((150, 150), detections) is True
    
    # Промах
    assert check_hit((50, 50), detections) is False

"""Тесты для модуля расчёта упреждения."""

import pytest

from src.analysis.lead import lead_offset, time_of_flight


class TestTimeOfFlight:
    """Тесты времени полёта пули."""

    def test_equal_distance_and_speed(self):
        """При равных distance и speed время полёта равно 1."""
        assert time_of_flight(850.0, 850.0) == pytest.approx(1.0)

    def test_zero_distance(self):
        """Нулевая дистанция — нулевое время."""
        assert time_of_flight(0.0, 850.0) == pytest.approx(0.0)

    def test_negative_distance_raises(self):
        """Отрицательная дистанция вызывает ValueError."""
        with pytest.raises(ValueError):
            time_of_flight(-1.0, 850.0)

    def test_zero_bullet_speed_raises(self):
        """Нулевая скорость пули вызывает ValueError."""
        with pytest.raises(ValueError):
            time_of_flight(100.0, 0.0)


class TestLeadOffset:
    """Тесты расчёта упреждения."""

    def test_stationary_target(self):
        """Неподвижная цель — упреждение ноль."""
        assert lead_offset((0.0, 0.0), 850.0, 850.0) == (0.0, 0.0)

    def test_horizontal_velocity(self):
        """Горизонтальная скорость даёт только dx."""
        result = lead_offset((10.0, 0.0), 850.0, 850.0)
        assert result == pytest.approx((10.0, 0.0))

    def test_diagonal_velocity(self):
        """Диагональная скорость даёт оба компонента."""
        result = lead_offset((5.0, -3.0), 850.0, 850.0)
        assert result == pytest.approx((5.0, -3.0))

    def test_invalid_velocity_raises(self):
        """Некорректный вектор скорости вызывает ValueError."""
        with pytest.raises(ValueError):
            lead_offset((1.0,), 850.0, 850.0)

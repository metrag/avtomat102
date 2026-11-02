"""Тесты для модуля статистики сессии."""

from datetime import datetime, timedelta

import pytest

from src.analysis.session_stats import summarize


class TestSummarize:
    """Тесты сводки статистики по списку выстрелов."""

    def test_empty_list(self):
        """Пустой список выстрелов возвращает нулевую статистику."""
        result = summarize([])

        assert result["hits"] == 0
        assert result["misses"] == 0
        assert result["total"] == 0
        assert result["accuracy"] == 0.0
        assert result["accuracy_percent"] == 0.0
        assert result["avg_interval_sec"] == 0.0

    def test_single_hit(self):
        """Одиночное попадание даёт точность 100 %."""
        shots = [{"timestamp": datetime.now(), "hit": True}]
        result = summarize(shots)

        assert result["hits"] == 1
        assert result["misses"] == 0
        assert result["total"] == 1
        assert result["accuracy"] == pytest.approx(1.0)
        assert result["accuracy_percent"] == pytest.approx(100.0)
        assert result["avg_interval_sec"] == 0.0

    def test_single_miss(self):
        """Одиночный промах даёт нулевую точность."""
        shots = [{"timestamp": datetime.now(), "hit": False}]
        result = summarize(shots)

        assert result["hits"] == 0
        assert result["misses"] == 1
        assert result["total"] == 1
        assert result["accuracy"] == pytest.approx(0.0)
        assert result["accuracy_percent"] == pytest.approx(0.0)
        assert result["avg_interval_sec"] == 0.0

    def test_mixed_accuracy(self):
        """Смешанные попадания и промахи считаются корректно."""
        base = datetime.now()
        shots = [
            {"timestamp": base + timedelta(seconds=i), "hit": i % 2 == 0}
            for i in range(4)
        ]
        result = summarize(shots)

        assert result["hits"] == 2
        assert result["misses"] == 2
        assert result["total"] == 4
        assert result["accuracy"] == pytest.approx(0.5)
        assert result["accuracy_percent"] == pytest.approx(50.0)

    def test_avg_interval(self):
        """Средний интервал между выстрелами рассчитывается по меткам времени."""
        base = datetime(2026, 11, 2, 12, 0, 0)
        shots = [
            {"timestamp": base + timedelta(seconds=i * 2), "hit": True}
            for i in range(4)
        ]
        result = summarize(shots)

        assert result["avg_interval_sec"] == pytest.approx(2.0)

    def test_unsorted_shots(self):
        """Выстрелы сортируются по времени перед расчётом интервалов."""
        base = datetime(2026, 11, 2, 12, 0, 0)
        shots = [
            {"timestamp": base + timedelta(seconds=6), "hit": True},
            {"timestamp": base + timedelta(seconds=0), "hit": True},
            {"timestamp": base + timedelta(seconds=3), "hit": True},
        ]
        result = summarize(shots)

        assert result["avg_interval_sec"] == pytest.approx(3.0)

    def test_iso_timestamp(self):
        """Поддерживаются строки в формате ISO 8601."""
        shots = [
            {"timestamp": "2026-11-02T12:00:00", "hit": True},
            {"timestamp": "2026-11-02T12:00:02", "hit": False},
        ]
        result = summarize(shots)

        assert result["total"] == 2
        assert result["avg_interval_sec"] == pytest.approx(2.0)

    def test_time_only_timestamp(self):
        """Поддерживаются строки времени без даты."""
        shots = [
            {"timestamp": "12:00:00", "hit": True},
            {"timestamp": "12:00:05", "hit": True},
        ]
        result = summarize(shots)

        assert result["total"] == 2
        assert result["avg_interval_sec"] == pytest.approx(5.0)

    def test_integer_hit_values(self):
        """Целочисленные значения hit интерпретируются как булевы."""
        shots = [
            {"timestamp": datetime.now(), "hit": 1},
            {"timestamp": datetime.now(), "hit": 0},
            {"timestamp": datetime.now(), "hit": 2},
        ]
        result = summarize(shots)

        assert result["hits"] == 2
        assert result["misses"] == 1
        assert result["accuracy"] == pytest.approx(2 / 3)

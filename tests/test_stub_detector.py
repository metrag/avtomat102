"""Тесты заглушки детектора БПЛА."""

import numpy as np
import pytest

from src.analysis.hit_checker import check_hit
from src.detection.stub_detector import StubDetector


class TestStubDetector:
    """Проверка синтетической детекции в центре кадра."""

    def test_single_centered_detection(self):
        """Возвращается ровно одна детекция внутри кадра."""
        frame = np.zeros((120, 160, 3), dtype=np.uint8)

        detections = StubDetector().detect(frame)

        assert len(detections) == 1
        detection = detections[0]
        x1, y1, x2, y2 = detection.bbox
        assert 0 <= x1 < x2 <= 160
        assert 0 <= y1 < y2 <= 120
        assert detection.confidence == 1.0
        assert len(detection.contour) >= 3

    def test_hit_at_center_miss_far_away(self):
        """Прицел в центре — попадание, в углу — промах."""
        frame = np.zeros((120, 160, 3), dtype=np.uint8)
        detections = StubDetector().detect(frame)

        assert check_hit((80, 60), detections) is True
        assert check_hit((5, 5), detections) is False

    def test_empty_frame_raises(self):
        """Пустой кадр отклоняется."""
        with pytest.raises(ValueError):
            StubDetector().detect(np.zeros((0, 0, 3), dtype=np.uint8))

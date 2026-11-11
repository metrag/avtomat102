"""Заглушка детектора БПЛА до подключения YOLO.

Возвращает одну синтетическую детекцию в центре кадра, чтобы
протестировать конвейер «фото -> детекция -> проверка попадания».
"""

from typing import List

import numpy as np

from src.detection.detector import Detection


class StubDetector:
    """Заглушка детектора: «БПЛА» всегда в центре кадра."""

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """Возвращает одну синтетическую детекцию в центре кадра.

        Args:
            frame: BGR изображение (H, W, C).

        Returns:
            Список из одной Detection с квадратным контуром по центру.

        Raises:
            ValueError: Если кадр пустой.
        """
        if frame is None or frame.size == 0:
            raise ValueError("Передан пустой кадр")

        height, width = frame.shape[:2]
        side = max(min(height, width) // 4, 8)
        cx, cy = width // 2, height // 2
        x1, y1 = cx - side // 2, cy - side // 2
        x2, y2 = cx + side // 2, cy + side // 2

        return [
            Detection(
                bbox=np.array([x1, y1, x2, y2], dtype=float),
                contour=[(x1, y1), (x2, y1), (x2, y2), (x1, y2)],
                confidence=1.0,
                class_id=0,
            )
        ]

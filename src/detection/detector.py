"""Детектор БПЛА на основе YOLOv8s-seg с сегментацией."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np


class DetectionError(Exception):
    """Ошибка детекции объектов."""

    pass


@dataclass
class Detection:
    """Результат детекции.
    
    Attributes:
        bbox: Ограничивающая рамка [x1, y1, x2, y2].
        contour: Список точек контура [(x1, y1), (x2, y2), ...].
        confidence: Уверенность детекции (0.0-1.0).
        class_id: ID класса объекта.
    """

    bbox: np.ndarray  # [x1, y1, x2, y2]
    contour: List[Tuple[int, int]]  # Polygon points
    confidence: float
    class_id: int


class DroneDetector:
    """Детектор БПЛА на основе YOLOv8s-seg.
    
    Attributes:
        _model_path: Путь к файлу весов модели.
        _model: Экземпляр модели (ленивая инициализация).
        _confidence_threshold: Порог уверенности.
    """

    def __init__(
        self,
        model_path: str = "data/models/yolov8s-seg.pt",
        confidence_threshold: float = 0.5,
    ):
        """Инициализация детектора с ленивой загрузкой модели.
        
        Args:
            model_path: Путь к файлу .pt модели.
            confidence_threshold: Минимальная уверенность для отбора.
        """
        self._model_path = model_path
        self._model = None  # Ленивая инициализация
        self._confidence_threshold = confidence_threshold

    def _load_model(self):
        """Загружает модель при первом вызове.
        
        Raises:
            FileNotFoundError: Если файл модели отсутствует.
            DetectionError: Если не удалось загрузить модель.
        """
        path = Path(self._model_path)
        if not path.exists():
            raise FileNotFoundError(f"Модель не найдена: {self._model_path}")

        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise DetectionError(
                "Библиотека ultralytics не установлена. "
                "Установите зависимости: pip install -r requirements.txt"
            ) from exc

        try:
            self._model = YOLO(str(path))
        except Exception as exc:
            raise DetectionError(
                f"Не удалось загрузить модель {self._model_path}"
            ) from exc

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """Детектирует БПЛА на кадре.
        
        Args:
            frame: RGB изображение (H, W, C).
        
        Returns:
            Список детекций с bbox, contour (polygon), confidence, class_id.
        
        Raises:
            DetectionError: Если модель не загружена или инференс не удался.
            ValueError: Если кадр пустой.
        """
        if frame is None or frame.size == 0:
            raise ValueError("Передан пустой кадр")

        if self._model is None:
            self._load_model()

        try:
            results = self._model(frame, verbose=False)
        except Exception as exc:
            raise DetectionError("Ошибка инференса модели") from exc

        detections: List[Detection] = []

        for result in results:
            if result.masks is None:
                continue

            for mask, box in zip(result.masks, result.boxes):
                if box.conf.item() < self._confidence_threshold:
                    continue

                # Извлекаем контур из маски
                contour = self._mask_to_contour(mask.data.cpu().numpy())

                detections.append(
                    Detection(
                        bbox=box.xyxy[0].cpu().numpy(),  # [x1, y1, x2, y2]
                        contour=contour,  # List[Tuple[int, int]]
                        confidence=box.conf.item(),
                        class_id=int(box.cls.item()),
                    )
                )

        return detections

    def _mask_to_contour(self, mask: np.ndarray) -> List[Tuple[int, int]]:
        """Конвертирует binary mask в контур (список точек).
        
        Args:
            mask: Binary mask (H, W).
        
        Returns:
            Список точек [(x1, y1), (x2, y2), ...].
        """
        mask_uint8 = (mask * 255).astype(np.uint8)
        contours, _ = cv2.findContours(
            mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            return []

        # Берём largest contour
        largest_contour = max(contours, key=cv2.contourArea)
        return [(int(pt[0][0]), int(pt[0][1])) for pt in largest_contour]

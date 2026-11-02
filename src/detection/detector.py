"""Обёртка над YOLOv8s-seg для детекции и сегментации БПЛА."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


class DetectionError(Exception):
    """Ошибка детекции объектов."""

    pass


@dataclass
class Detection:
    """Результат детекции одного объекта.

    Attributes:
        class_name: Имя класса объекта.
        confidence: Уверенность детекции (0.0-1.0).
        bbox: Ограничивающая рамка (x_min, y_min, x_max, y_max).
        mask: Бинарная маска сегментации (HxW) или None.
    """

    class_name: str
    confidence: float
    bbox: tuple[int, int, int, int]
    mask: np.ndarray | None


class Detector:
    """Детектор БПЛА на базе YOLOv8s-seg.

    Attributes:
        model_path: Путь к файлу весов модели.
        confidence_threshold: Порог уверенности.
        device: Устройство инференса ('cpu' или 'cuda').
    """

    def __init__(
        self,
        model_path: str,
        confidence_threshold: float = 0.5,
        device: str = "cpu",
    ):
        """Инициализация детектора.

        Args:
            model_path: Путь к файлу .pt модели.
            confidence_threshold: Минимальная уверенность для отбора.
            device: Устройство инференса.
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.device = device
        self._model: Any | None = None

    def load_model(self) -> None:
        """Загружает модель YOLOv8 из файла весов.

        Raises:
            FileNotFoundError: Если файл модели отсутствует.
            DetectionError: Если не удалось загрузить модель.
        """
        path = Path(self.model_path)
        if not path.exists():
            raise FileNotFoundError(
                f"Файл модели не найден: {self.model_path}. "
                f"Поместите веса YOLOv8s-seg по указанному пути."
            )

        # Импорт внутри метода, чтобы приложение не падало при импорте модуля,
        # если ultralytics не установлена.
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
            raise DetectionError(f"Не удалось загрузить модель {self.model_path}") from exc

    def detect(self, frame: np.ndarray) -> list[Detection]:
        """Выполняет детекцию на кадре.

        Args:
            frame: Изображение BGR (HxWx3).

        Returns:
            Список обнаруженных объектов.

        Raises:
            DetectionError: Если модель не загружена или инференс не удался.
            ValueError: Если кадр пустой.
        """
        if frame is None or frame.size == 0:
            raise ValueError("Передан пустой кадр")

        if self._model is None:
            self.load_model()

        try:
            results = self._model.predict(
                frame,
                conf=self.confidence_threshold,
                device=self.device,
                verbose=False,
            )
        except Exception as exc:
            raise DetectionError("Ошибка инференса модели") from exc

        detections: list[Detection] = []
        if not results:
            return detections

        result = results[0]
        boxes = result.boxes
        masks = result.masks

        if boxes is None:
            return detections

        for index, box in enumerate(boxes):
            x_min, y_min, x_max, y_max = box.xyxy[0].cpu().numpy().astype(int)
            confidence = float(box.conf[0])
            class_id = int(box.cls[0])
            class_name = result.names.get(class_id, str(class_id))

            mask = None
            if masks is not None and masks.data is not None and index < len(masks.data):
                mask_tensor = masks.data[index]
                mask = mask_tensor.cpu().numpy().astype(np.uint8)

            detections.append(
                Detection(
                    class_name=class_name,
                    confidence=confidence,
                    bbox=(x_min, y_min, x_max, y_max),
                    mask=mask,
                )
            )

        return detections

"""Тесты для детектора БПЛА."""

import numpy as np
import pytest

from src.detection.detector import Detection, DroneDetector


def test_detection_dataclass():
    """Тест структуры Detection."""
    detection = Detection(
        bbox=np.array([100, 100, 200, 200]),
        contour=[(100, 100), (200, 100), (200, 200), (100, 200)],
        confidence=0.95,
        class_id=0
    )
    assert detection.confidence == 0.95
    assert len(detection.contour) == 4
    assert detection.class_id == 0
    assert np.array_equal(detection.bbox, np.array([100, 100, 200, 200]))


def test_mask_to_contour():
    """Тест конвертации mask → contour."""
    detector = DroneDetector(model_path="dummy.pt")
    
    # Создаём synthetic mask (квадрат)
    mask = np.zeros((100, 100), dtype=np.float32)
    mask[20:80, 20:80] = 1.0
    
    contour = detector._mask_to_contour(mask)
    
    assert len(contour) >= 4  # Минимум 4 точки для прямоугольника
    # Все точки должны быть в пределах маски
    for x, y in contour:
        assert 0 <= x < 100
        assert 0 <= y < 100


def test_mask_to_contour_empty():
    """Тест конвертации пустой маски."""
    detector = DroneDetector(model_path="dummy.pt")
    
    # Создаём пустую маску
    mask = np.zeros((100, 100), dtype=np.float32)
    
    contour = detector._mask_to_contour(mask)
    
    assert len(contour) == 0


def test_mask_to_contour_triangle():
    """Тест конвертации маски с треугольником."""
    detector = DroneDetector(model_path="dummy.pt")
    
    # Создаём маску с треугольником
    mask = np.zeros((100, 100), dtype=np.float32)
    # Простой треугольник
    mask[30:70, 30:70] = 1.0
    mask[10:30, 40:60] = 1.0
    
    contour = detector._mask_to_contour(mask)
    
    assert len(contour) >= 3  # Минимум 3 точки для треугольника


def test_detector_initialization():
    """Тест инициализации детектора."""
    detector = DroneDetector(
        model_path="test_model.pt",
        confidence_threshold=0.7
    )
    
    assert detector._model_path == "test_model.pt"
    assert detector._confidence_threshold == 0.7
    assert detector._model is None  # Ленивая инициализация


def test_detector_lazy_loading():
    """Тест ленивой загрузки модели."""
    detector = DroneDetector(model_path="nonexistent.pt")
    
    # Модель не должна быть загружена при инициализации
    assert detector._model is None
    
    # При вызове detect() должно произойти исключение FileNotFoundError
    # так как модель не существует
    with pytest.raises(FileNotFoundError, match="Модель не найдена"):
        detector.detect(np.zeros((100, 100, 3), dtype=np.uint8))


def test_detection_with_numpy_bbox():
    """Тест Detection с numpy массивом для bbox."""
    bbox = np.array([10.5, 20.3, 30.7, 40.9])
    detection = Detection(
        bbox=bbox,
        contour=[(10, 20), (30, 20), (30, 40), (10, 40)],
        confidence=0.88,
        class_id=1
    )
    
    assert detection.confidence == 0.88
    assert detection.class_id == 1
    assert isinstance(detection.bbox, np.ndarray)

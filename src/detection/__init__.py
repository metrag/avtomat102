"""Модуль детекции БПЛА."""

from src.detection.detector import Detection, DetectionError, DroneDetector

__all__ = ["DroneDetector", "Detection", "DetectionError"]

"""Диалог калибровки смещения прицела по клику на кадре."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from src.utils.config import load_config

logger = logging.getLogger(__name__)

CALIBRATION_PATH = Path("data/calibration/calibration.json")


class CalibrationDialog(QDialog):
    """Диалог калибровки прицела.

    Пользователь кликает по кадру; вычисляется смещение от центра,
    которое сохраняется в data/calibration/calibration.json.
    """

    def __init__(self, parent=None) -> None:
        """Инициализация диалога калибровки.

        Args:
            parent: Родительский виджет.
        """
        super().__init__(parent)
        self.setWindowTitle("Калибровка прицела")


        self._config = load_config()
        self._offset: tuple[int, int] | None = None
        self._center: tuple[int, int] | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        """Создаёт интерфейс диалога."""
        layout = QVBoxLayout(self)

        info = QLabel(
            "Шаг 1. Ведите огонь по мишени и определите точку реального попадания.\n"
            "Шаг 2. Кликните по этой точке на кадре — смещение от центра\n"
            "будет сохранено и применено при засчёте попаданий."
        )
        info.setObjectName("calib_hint")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)

        self._image_label = QLabel()
        self._image_label.setObjectName("calib_frame")
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setMinimumSize(640, 480)
        self._image_label.setMouseTracking(True)
        self._image_label.mousePressEvent = self._on_mouse_press
        layout.addWidget(self._image_label)

        self._offset_label = QLabel("Смещение: не задано")
        layout.addWidget(self._offset_label)

        buttons_layout = QHBoxLayout()
        save_button = QPushButton("Готов")
        save_button.setObjectName("accent")
        save_button.clicked.connect(self._on_save)
        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addStretch()
        buttons_layout.addWidget(save_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)

        self._render_sample_frame()

    def _render_sample_frame(self) -> None:
        """Отрисовывает образец кадра с прицелом по центру."""
        width, height = 640, 480
        self._center = (width // 2, height // 2)

        frame = np.zeros((height, width, 3), dtype=np.uint8)
        # Рисуем перекрестие в центре.
        cx, cy = self._center
        cv2.line(frame, (cx - 20, cy), (cx + 20, cy), (0, 255, 0), 2)
        cv2.line(frame, (cx, cy - 20), (cx, cy + 20), (0, 255, 0), 2)
        cv2.circle(frame, (cx, cy), 10, (0, 255, 0), 2)

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channels = rgb_frame.shape
        bytes_per_line = channels * width
        qimage = QImage(
            rgb_frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888
        )
        self._image_label.setPixmap(QPixmap.fromImage(qimage))

    def _on_mouse_press(self, event) -> None:
        """Обрабатывает клик по образцу кадра.

        Args:
            event: Событие мыши.
        """
        if self._center is None:
            return

        pos = event.pos()
        offset_x = pos.x() - self._center[0]
        offset_y = pos.y() - self._center[1]
        self._offset = (offset_x, offset_y)
        self._offset_label.setText(f"Смещение: x={offset_x}, y={offset_y}")
        logger.info("Calibration offset selected: %s", self._offset)

    def _on_save(self) -> None:
        """Сохраняет калибровочные данные в JSON-файл."""
        if self._offset is None or self._center is None:
            QMessageBox.warning(
                self,
                "Калибровка не завершена",
                "Сначала кликните по точке попадания на кадре.",
            )
            return

        data = {
            "offset_x": self._offset[0],
            "offset_y": self._offset[1],
            "center": list(self._center),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        CALIBRATION_PATH.parent.mkdir(parents=True, exist_ok=True)
        with CALIBRATION_PATH.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

        logger.info("Calibration saved to %s", CALIBRATION_PATH)
        QMessageBox.information(self, "Готово", "Калибровка сохранена.")
        self.accept()

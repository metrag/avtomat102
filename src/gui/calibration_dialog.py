"""Диалог калибровки прицела по фото выстрела.

Пользователь дожидается фото с камеры (кнопка на плате — тот же выстрел,
что и в занятии), кликает по точке попадания на фото; смещение от центра
кадра сохраняется в data/calibration/calibration.json. Кнопка «Заново»
сбрасывает результат и ожидает новый выстрел.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from src.utils.window_utils import set_window_icon

logger = logging.getLogger(__name__)

CALIBRATION_PATH = Path("data/calibration/calibration.json")


def load_calibration() -> dict | None:
    """Возвращает сохранённые данные калибровки или None, если их нет.

    Returns:
        Словарь с полями offset_x/offset_y или None.
    """
    if not CALIBRATION_PATH.exists():
        return None
    try:
        with CALIBRATION_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to read calibration: %s", exc)
        return None
    if "offset_x" not in data or "offset_y" not in data:
        return None
    return data


def clear_calibration() -> None:
    """Удаляет сохранённый файл калибровки.

    Вызывается при старте приложения: прошлая калибровка не должна
    действовать без повторного выполнения тренером.
    """
    if not CALIBRATION_PATH.exists():
        return
    try:
        CALIBRATION_PATH.unlink()
        logger.info("Old calibration file removed: %s", CALIBRATION_PATH)
    except OSError as exc:
        logger.warning("Failed to remove calibration file: %s", exc)


class _ClickablePhotoLabel(QLabel):
    """Метка с фото выстрела: клик отмечает точку попадания."""

    # Координаты точки в кадре (не в координатах виджета).
    mark_selected = pyqtSignal(int, int)

    def __init__(self, parent=None) -> None:
        """Инициализация метки с фото.

        Args:
            parent: Родительский виджет.
        """
        super().__init__(parent)
        self._photo: QPixmap | None = None
        self._mark: tuple[int, int] | None = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(640, 480)
        self.setStyleSheet("background-color: #1a1a1a; color: #ffffff;")
        self.setText("Ожидание фото с камеры…")

    def set_photo(self, photo: QPixmap) -> None:
        """Показывает новое фото, сбрасывая прежнюю отметку.

        Args:
            photo: Фото выстрела.
        """
        self._photo = photo
        self._mark = None
        self._render()

    def clear_photo(self) -> None:
        """Убирает фото и возвращает метку в состояние ожидания."""
        self._photo = None
        self._mark = None
        self.setText("Ожидание фото с камеры…")

    def mousePressEvent(self, event) -> None:
        """Отмечает точку попадания по клику на фото.

        Args:
            event: Событие мыши.
        """
        rect = self._scaled_rect()
        if rect is None:
            return
        dx, dy, sw, sh = rect
        x = event.pos().x()
        y = event.pos().y()
        if not (dx <= x < dx + sw and dy <= y < dy + sh):
            return  # Клик мимо изображения.

        fw = self._photo.width()
        fh = self._photo.height()
        img_x = min(max(int((x - dx) * fw / sw), 0), fw - 1)
        img_y = min(max(int((y - dy) * fh / sh), 0), fh - 1)
        self._mark = (img_x, img_y)
        self._render()
        self.mark_selected.emit(img_x, img_y)

    def resizeEvent(self, event) -> None:
        """Перерисовывает фото при изменении размера виджета.

        Args:
            event: Событие изменения размера.
        """
        super().resizeEvent(event)
        if self._photo is not None:
            self._render()

    def _scaled_rect(self) -> tuple[float, float, float, float] | None:
        """Возвращает положение масштабированного фото внутри виджета.

        Returns:
            Кортеж (dx, dy, ширина, высота) или None, если фото нет.
        """
        if self._photo is None or self._photo.isNull():
            return None
        fw = self._photo.width()
        fh = self._photo.height()
        width = self.width()
        height = self.height()
        if width <= 0 or height <= 0 or fw <= 0 or fh <= 0:
            return None
        scale = min(width / fw, height / fh)
        sw = fw * scale
        sh = fh * scale
        return (width - sw) / 2, (height - sh) / 2, sw, sh

    def _render(self) -> None:
        """Рисует фото с перекрестием центра и отметкой попадания."""
        if self._photo is None:
            return
        pixmap = self._photo.copy()
        painter = QPainter(pixmap)
        fw = pixmap.width()
        fh = pixmap.height()

        # Перекрестие в центре кадра.
        cx, cy = fw // 2, fh // 2
        painter.setPen(QPen(QColor(0, 255, 0), 2))
        painter.drawLine(cx - 20, cy, cx + 20, cy)
        painter.drawLine(cx, cy - 20, cx, cy + 20)
        painter.drawEllipse(cx - 10, cy - 10, 20, 20)

        # Отметка точки попадания.
        if self._mark is not None:
            mx, my = self._mark
            painter.setPen(QPen(QColor(255, 64, 64), 2))
            painter.drawEllipse(mx - 10, my - 10, 20, 20)
            painter.drawLine(mx - 14, my, mx + 14, my)
            painter.drawLine(mx, my - 14, mx, my + 14)
        painter.end()

        self.setText("")
        self.setPixmap(
            pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )


class CalibrationDialog(QDialog):
    """Диалог калибровки прицела по фото выстрела.

    Фото приходит из главного окна (кнопка на камере = выстрел);
    пользователь отмечает точку попадания, смещение от центра кадра
    сохраняется в data/calibration/calibration.json. Кнопка «Заново»
    повторяет процедуру с новым выстрелом.
    """

    def __init__(self, parent=None) -> None:
        """Инициализация диалога калибровки.

        Args:
            parent: Родительский виджет.
        """
        super().__init__(parent)
        set_window_icon(self)
        self.setWindowTitle("Калибровка прицела")
        self._offset: tuple[int, int] | None = None
        self._center: tuple[int, int] | None = None
        self.saved = False  # True — только после сохранения через «Готов».

        self._build_ui()

    def _build_ui(self) -> None:
        """Создаёт интерфейс диалога."""
        layout = QVBoxLayout(self)

        info = QLabel(
            "1) Нажмите кнопку на камере — придёт фото выстрела\n"
            "2) Кликните по точке попадания на фото\n"
            "3) Нажмите «Готов». «Заново» — повторить выстрел."
        )
        info.setObjectName("calib_hint")
        info.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(info)

        self._photo_label = _ClickablePhotoLabel()
        self._photo_label.mark_selected.connect(self._on_mark_selected)
        layout.addWidget(self._photo_label, stretch=1)

        self._status_label = QLabel("Ожидание фото с камеры…")
        layout.addWidget(self._status_label)

        self._offset_label = QLabel("Смещение: не задано")
        layout.addWidget(self._offset_label)

        buttons_layout = QHBoxLayout()
        self._redo_button = QPushButton("Заново")
        self._redo_button.clicked.connect(self._on_redo)
        self._save_button = QPushButton("Готов")
        self._save_button.setObjectName("accent")
        self._save_button.setEnabled(False)
        self._save_button.clicked.connect(self._on_save)
        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self._redo_button)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self._save_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)

    def set_photo(self, photo: QPixmap) -> None:
        """Принимает фото выстрела из главного окна.

        Args:
            photo: Фото выстрела.
        """
        width, height = photo.width(), photo.height()
        self._center = (width // 2, height // 2)
        self._offset = None
        self._photo_label.set_photo(photo)
        self._offset_label.setText("Смещение: не задано")
        self._save_button.setEnabled(False)
        self._status_label.setText(
            f"Фото получено ({width}×{height}). Отметьте точку попадания кликом."
        )
        logger.info("Calibration photo received: %dx%d", width, height)

    def _on_mark_selected(self, x: int, y: int) -> None:
        """Обрабатывает отметку точки попадания на фото.

        Args:
            x: Координата X в кадре.
            y: Координата Y в кадре.
        """
        if self._center is None:
            return
        offset = (x - self._center[0], y - self._center[1])
        self._offset = offset
        self._offset_label.setText(
            f"Смещение: x={offset[0]:+d}, y={offset[1]:+d} (точка {x}, {y})"
        )
        self._status_label.setText(
            "Точка отмечена. «Готов» — сохранить, «Заново» — повторить."
        )
        self._save_button.setEnabled(True)
        logger.info("Calibration offset selected: %s", self._offset)

    def _on_redo(self) -> None:
        """Сбрасывает результат и ожидает новый выстрел."""
        self._offset = None
        self._center = None
        self._photo_label.clear_photo()
        self._offset_label.setText("Смещение: не задано")
        self._save_button.setEnabled(False)
        self._status_label.setText("Ожидание фото с камеры…")
        logger.info("Calibration reset — waiting for a new shot")

    def _on_save(self) -> None:
        """Сохраняет калибровочные данные в JSON-файл."""
        if self._offset is None or self._center is None:
            QMessageBox.warning(
                self,
                "Калибровка не завершена",
                "Сначала отметьте точку попадания на фото.",
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

        self.saved = True
        logger.info("Calibration saved to %s: %s", CALIBRATION_PATH, data)
        QMessageBox.information(self, "Готово", "Калибровка сохранена.")
        self.accept()

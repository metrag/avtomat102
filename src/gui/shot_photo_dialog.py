"""Диалог просмотра кадра, сохранённого для выстрела."""

import logging
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.utils.window_utils import set_window_icon

logger = logging.getLogger(__name__)

_MAX_WIDTH = 640
_MAX_HEIGHT = 480


class ShotPhotoDialog(QDialog):
    """Показывает фото выстрела или плейсхолдер, если кадра нет."""

    def __init__(
        self,
        shot_no: int,
        photo_path: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Инициализация диалога просмотра.

        Args:
            shot_no: Порядковый номер выстрела.
            photo_path: Путь к JPG-файлу или None.
            parent: Родительский виджет.
        """
        super().__init__(parent)
        set_window_icon(self)
        self.setWindowTitle(f"Выстрел №{shot_no}")
        self.setModal(True)
        self._build_ui(photo_path)
        logger.info("Photo dialog for shot %s: %s", shot_no, photo_path)

    def _build_ui(self, photo_path: str | None) -> None:
        """Создаёт элементы диалога.

        Args:
            photo_path: Путь к JPG-файлу или None.
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        image_label = QLabel()
        image_label.setObjectName("calib_frame")
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setMinimumSize(_MAX_WIDTH // 2, _MAX_HEIGHT // 2)

        pixmap = self._load_pixmap(photo_path)
        if pixmap is not None:
            image_label.setPixmap(
                pixmap.scaled(
                    _MAX_WIDTH,
                    _MAX_HEIGHT,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            image_label.setText("Фото не сохранено")
            image_label.setPixmap(self._placeholder())

        layout.addWidget(image_label)

        close_button = QPushButton("Закрыть")
        close_button.setObjectName("accent")
        close_button.setFixedWidth(160)
        close_button.clicked.connect(self.accept)
        button_row = QVBoxLayout()
        button_row.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(button_row)

    @staticmethod
    def _load_pixmap(photo_path: str | None) -> QPixmap | None:
        """Загружает pixmap из файла, если он существует.

        Args:
            photo_path: Путь к JPG-файлу или None.

        Returns:
            QPixmap или None.
        """
        if not photo_path:
            return None
        path = Path(photo_path)
        if not path.exists():
            return None
        pixmap = QPixmap(str(path))
        return pixmap if not pixmap.isNull() else None

    @staticmethod
    def _placeholder() -> QPixmap:
        """Создаёт заглушку вместо отсутствующего кадра.

        Returns:
            QPixmap с текстом «Кадр не сохранён».
        """
        image = QImage(_MAX_WIDTH, _MAX_HEIGHT, QImage.Format.Format_RGB32)
        image.fill(QColor("#1A1A1A"))
        painter = QPainter(image)
        painter.setPen(QColor("#888888"))
        painter.drawText(
            image.rect(),
            int(Qt.AlignmentFlag.AlignCenter),
            "Кадр не сохранён",
        )
        painter.end()
        return QPixmap.fromImage(image)

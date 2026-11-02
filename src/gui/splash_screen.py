"""Заставка — первое окно приложения тренажёра."""

import logging
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)

_GERB_PATH = Path(__file__).resolve().parents[2] / "assets" / "images" / "gerb.png"
_MAX_IMAGE_SIZE = 400


class SplashScreen(QDialog):
    """Заставка с гербом, названием проекта и кнопкой «Далее»."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Инициализация заставки.

        Args:
            parent: Родительский виджет.
        """
        super().__init__(parent)
        self.setWindowTitle("Тренажёр стрельбы по БПЛА")
        self.setFixedSize(760, 560)
        self._build_ui()
        logger.info("Splash screen shown")

    def _build_ui(self) -> None:
        """Создаёт элементы заставки."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(16)

        spacer_top = QWidget()
        spacer_top.setFixedHeight(8)
        layout.addWidget(spacer_top)

        # Герб — изображение из assets/images/gerb.png.
        image_label = QLabel()
        image_label.setObjectName("splash_image")
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setMinimumHeight(200)
        image_label.setPixmap(self._load_gerb())
        layout.addWidget(image_label, alignment=Qt.AlignmentFlag.AlignCenter)

        title = QLabel(
            "Оптико-электронный интерактивный\n"
            "тренажёр для отработки стрельбы\n"
            "по БПЛА"
        )
        title.setObjectName("splash_title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setWordWrap(True)
        layout.addWidget(title)

        layout.addStretch()

        next_button = QPushButton("Далее →")
        next_button.setObjectName("accent")
        next_button.setFixedWidth(220)
        next_button.clicked.connect(self.accept)
        button_row = QVBoxLayout()
        button_row.addWidget(next_button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(button_row)

    @staticmethod
    def _load_gerb() -> "QPixmap":
        """Загружает герб из assets/images/gerb.png.

        Returns:
            QPixmap с изображением герба или плейсхолдер, если файл отсутствует.
        """
        from PyQt6.QtGui import QColor, QImage, QPainter, QPixmap

        if _GERB_PATH.exists():
            pixmap = QPixmap(str(_GERB_PATH))
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    _MAX_IMAGE_SIZE,
                    _MAX_IMAGE_SIZE,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                logger.info("Gerb loaded: %s (%dx%d)", _GERB_PATH, scaled.width(), scaled.height())
                return scaled
            logger.warning("Gerb file found but QPixmap is null: %s", _GERB_PATH)
        else:
            logger.warning("Gerb file not found: %s", _GERB_PATH)

        # Плейсхолдер, если файл отсутствует или не читается.
        placeholder = QImage(_MAX_IMAGE_SIZE, _MAX_IMAGE_SIZE, QImage.Format.Format_RGB32)
        placeholder.fill(QColor("#1A1A1A"))
        painter = QPainter(placeholder)
        painter.setPen(QColor("#888888"))
        painter.drawText(
            placeholder.rect(),
            int(Qt.AlignmentFlag.AlignCenter),
            "[герб не загружен]",
        )
        painter.end()
        return QPixmap.fromImage(placeholder)

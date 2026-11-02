"""Заставка — первое окно приложения тренажёра."""

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class SplashScreen(QDialog):
    """Заставка с названием проекта и кнопкой «Далее»."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Инициализация заставки.

        Args:
            parent: Родительский виджет.
        """
        super().__init__(parent)
        self.setWindowTitle("Тренажёр стрельбы по БПЛА")
        self.setFixedSize(720, 460)
        self._build_ui()
        logger.info("Splash screen shown")

    def _build_ui(self) -> None:
        """Создаёт элементы заставки."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(16)

        spacer_top = QWidget()
        spacer_top.setFixedHeight(24)
        layout.addWidget(spacer_top)

        title = QLabel("ТРЕНАЖЁР СТРЕЛЬБЫ ПО БПЛА")
        title.setObjectName("splash_title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Интерактивный программно-аппаратный тренажёр\n"
                          "отработки стрельбы по беспилотным летательным аппаратам")
        subtitle.setObjectName("splash_subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        team = QLabel(
            "Курсанты 631/12 уч. гр.: Хазиев Г.Р., Скрыпник Е.М., Гусев А.Д.\n"
            "Руководитель: полк. Карпов В.Б.\n"
            "102 кафедра"
        )
        team.setObjectName("splash_team")
        team.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(team)

        layout.addStretch()

        next_button = QPushButton("Далее →")
        next_button.setObjectName("accent")
        next_button.setFixedWidth(220)
        next_button.clicked.connect(self.accept)
        button_row = QVBoxLayout()
        button_row.addWidget(next_button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(button_row)

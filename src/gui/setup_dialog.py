"""Диалог настройки занятия: данные курсанта и параметры стрельбы."""

import logging
from typing import Any

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)

RANKS = ["Курсант", "Мл. сержант", "Сержант", "Ст. сержант", "Прапорщик", "Лейтенант"]
MODES = ["Автоматический", "Ручной"]
DISTANCE_PRESETS = ["50", "70", "100", "150", "200", "Своя..."]
CUSTOM_DISTANCE_TEXT = "Своя..."


class SetupDialog(QDialog):
    """Форма настройки занятия перед выходом в главное окно."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Инициализация диалога настройки.

        Args:
            parent: Родительский виджет.
        """
        super().__init__(parent)
        self.setWindowTitle("Настройка занятия")
        self.setMinimumWidth(460)
        self._build_ui()
        logger.info("Setup dialog shown")

    def _build_ui(self) -> None:
        """Создаёт поля формы."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QLabel("Параметры тренировочного занятия")
        header.setObjectName("setup_header")
        layout.addWidget(header)

        form = QFormLayout()
        form.setSpacing(12)

        self._rank_combo = QComboBox()
        self._rank_combo.addItems(RANKS)
        form.addRow("Воинское звание:", self._rank_combo)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Иванов Иван Иванович")
        form.addRow("ФИО:", self._name_edit)

        self._group_edit = QLineEdit()
        self._group_edit.setPlaceholderText("631/12")
        form.addRow("№ учебной группы:", self._group_edit)

        self._mode_combo = QComboBox()
        self._mode_combo.addItems(MODES)
        self._mode_combo.setToolTip(
            "Автоматический: детекция сама засчитывает выстрел.\n"
            "Ручной: тренер отмечает попадание/промах кнопками."
        )
        form.addRow("Режим стрельбы:", self._mode_combo)

        distance_row = QHBoxLayout()
        self._distance_combo = QComboBox()
        self._distance_combo.addItems(DISTANCE_PRESETS)
        self._distance_combo.currentTextChanged.connect(self._on_distance_changed)
        distance_row.addWidget(self._distance_combo)

        self._custom_distance_edit = QLineEdit()
        self._custom_distance_edit.setPlaceholderText("Своя, м")
        self._custom_distance_edit.setEnabled(False)
        distance_row.addWidget(self._custom_distance_edit)
        form.addRow("Дистанция, м:", distance_row)

        self._ammo_spin = QSpinBox()
        self._ammo_spin.setRange(1, 300)
        self._ammo_spin.setValue(30)
        form.addRow("Количество патронов:", self._ammo_spin)

        layout.addLayout(form)
        layout.addStretch()

        buttons = QHBoxLayout()
        buttons.addStretch()

        start_button = QPushButton("Начать")
        start_button.setObjectName("accent")
        start_button.setFixedWidth(160)
        start_button.clicked.connect(self._on_accept)
        buttons.addWidget(start_button)

        cancel_button = QPushButton("Отмена")
        cancel_button.setFixedWidth(120)
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(cancel_button)

        layout.addLayout(buttons)

    def _on_distance_changed(self, text: str) -> None:
        """Переключает поле собственной дистанции при выборе «Своя...».

        Args:
            text: Выбранный текст в комбобоксе.
        """
        self._custom_distance_edit.setEnabled(text == CUSTOM_DISTANCE_TEXT)
        if text == CUSTOM_DISTANCE_TEXT:
            self._custom_distance_edit.setFocus()
        else:
            self._custom_distance_edit.clear()

    def _resolve_distance(self) -> int | None:
        """Определяет дистанцию из пресета или собственного поля.

        Returns:
            Дистанция в метрах или None, если значение некорректно.
        """
        if self._distance_combo.currentText() != CUSTOM_DISTANCE_TEXT:
            try:
                return int(self._distance_combo.currentText())
            except ValueError:
                return None

        text = self._custom_distance_edit.text().strip()
        try:
            value = int(text)
        except ValueError:
            return None
        return value if 1 <= value <= 10000 else None

    def _on_accept(self) -> None:
        """Проверяет поля и закрывает диалог с результатом."""
        name = self._name_edit.text().strip()
        group = self._group_edit.text().strip()
        distance = self._resolve_distance()

        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите ФИО курсанта.")
            self._name_edit.setFocus()
            return
        if not group:
            QMessageBox.warning(self, "Ошибка", "Введите номер учебной группы.")
            self._group_edit.setFocus()
            return
        if distance is None:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Укажите корректную дистанцию (число от 1 до 10000 м).",
            )
            self._custom_distance_edit.setFocus()
            return

        logger.info(
            "Setup accepted: name=%s group=%s mode=%s distance=%s",
            name,
            group,
            self._mode_combo.currentText(),
            distance,
        )
        self.accept()

    def data(self) -> dict[str, Any]:
        """Возвращает данные заполненной формы.

        Returns:
            Словарь: rank, full_name, group_no, mode, distance, ammo.
        """
        return {
            "rank": self._rank_combo.currentText(),
            "full_name": self._name_edit.text().strip(),
            "group_no": self._group_edit.text().strip(),
            "mode": self._mode_combo.currentText(),
            "distance": self._resolve_distance(),
            "ammo": self._ammo_spin.value(),
        }

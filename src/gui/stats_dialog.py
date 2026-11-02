"""Диалог сводки статистики последней сессии."""

import logging
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.analysis.session_stats import summarize
from src.storage.journal import ShotJournal
from src.storage.report import ReportError, export_report

logger = logging.getLogger(__name__)


class StatsDialog(QDialog):
    """Диалог отображения сводки по последней тренировочной сессии."""

    def __init__(
        self,
        journal: ShotJournal | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Инициализация диалога статистики.

        Args:
            journal: Журнал выстрелов. Если не указан, создаётся экземпляр
                по умолчанию из конфигурации.
            parent: Родительский виджет.
        """
        super().__init__(parent)
        self.setWindowTitle("Статистика сессии")
        self.resize(700, 500)

        self._journal = journal or ShotJournal()
        self._session_id: int | None = None

        self._build_ui()
        self._load_stats()

    def _build_ui(self) -> None:
        """Создаёт компоновку диалога."""
        layout = QVBoxLayout(self)

        # Блок сводных показателей.
        summary_layout = QHBoxLayout()
        self._hits_label = QLabel("Попаданий: —")
        self._misses_label = QLabel("Промахов: —")
        self._accuracy_label = QLabel("Точность: —")
        self._interval_label = QLabel("Средний интервал: —")

        for label in (
            self._hits_label,
            self._misses_label,
            self._accuracy_label,
            self._interval_label,
        ):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            summary_layout.addWidget(label)

        layout.addLayout(summary_layout)

        # Таблица выстрелов.
        self._shots_table = QTableWidget(0, 4)
        self._shots_table.setHorizontalHeaderLabels(
            ["№", "Время", "Результат", "Координаты"]
        )
        self._shots_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self._shots_table)

        # Кнопки экспорта и закрытия.
        buttons_row = QHBoxLayout()

        csv_button = QPushButton("Экспорт CSV")
        csv_button.clicked.connect(lambda: self._export("csv"))
        buttons_row.addWidget(csv_button)

        txt_button = QPushButton("Экспорт TXT")
        txt_button.clicked.connect(lambda: self._export("txt"))
        buttons_row.addWidget(txt_button)

        buttons_row.addStretch()

        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.accept)
        buttons_row.addWidget(close_button)

        layout.addLayout(buttons_row)

    def _export(self, fmt: str) -> None:
        """Экспортирует отчёт текущей сессии и показывает путь к файлу.

        Args:
            fmt: Формат файла — 'csv' или 'txt'.
        """
        if self._session_id is None:
            QMessageBox.warning(self, "Экспорт", "Нет сессии для экспорта.")
            return

        try:
            path = export_report(self._journal, self._session_id, fmt=fmt)
        except ReportError as exc:
            logger.error("Export failed: %s", exc)
            QMessageBox.warning(self, "Ошибка экспорта", str(exc))
            return

        QMessageBox.information(self, "Экспорт", f"Отчёт сохранён:\n{path}")

    def _load_stats(self) -> None:
        """Загружает и отображает статистику последней сессии."""
        sessions = self._journal.get_sessions()
        if not sessions:
            self._set_empty_state("Нет сохранённых сессий")
            return

        last_session_id = sessions[-1]["id"]
        self._session_id = last_session_id
        shots = self._journal.get_shots(last_session_id)
        if not shots:
            self._set_empty_state("В последней сессии нет выстрелов")
            return

        stats = summarize(shots)
        self._hits_label.setText(f"Попаданий: {stats['hits']}")
        self._misses_label.setText(f"Промахов: {stats['misses']}")
        self._accuracy_label.setText(
            f"Точность: {stats['accuracy_percent']:.1f}%"
        )
        self._interval_label.setText(
            f"Средний интервал: {stats['avg_interval_sec']:.2f} с"
        )

        self._shots_table.setRowCount(0)
        for index, shot in enumerate(shots, start=1):
            row = self._shots_table.rowCount()
            self._shots_table.insertRow(row)

            self._shots_table.setItem(row, 0, QTableWidgetItem(str(index)))
            self._shots_table.setItem(
                row, 1, QTableWidgetItem(self._format_time(shot.get("timestamp", "")))
            )

            hit = bool(shot.get("hit"))
            result_text = "Попадание" if hit else "Промах"
            result_item = QTableWidgetItem(result_text)
            result_item.setForeground(
                Qt.GlobalColor.green if hit else Qt.GlobalColor.red
            )
            self._shots_table.setItem(row, 2, result_item)

            aim_x = shot.get("aim_x")
            aim_y = shot.get("aim_y")
            coords = f"{aim_x}, {aim_y}" if aim_x is not None and aim_y is not None else "—"
            self._shots_table.setItem(row, 3, QTableWidgetItem(coords))

    def _set_empty_state(self, message: str) -> None:
        """Отображает сообщение об отсутствии данных.

        Args:
            message: Текст сообщения.
        """
        self._hits_label.setText(message)
        self._misses_label.setText("")
        self._accuracy_label.setText("")
        self._interval_label.setText("")
        self._shots_table.setRowCount(0)

    @staticmethod
    def _format_time(value: Any) -> str:
        """Форматирует метку времени для отображения.

        Args:
            value: Метка времени (строка ISO 8601 или другая строка).

        Returns:
            Строка времени в формате ЧЧ:ММ:СС.
        """
        if not isinstance(value, str) or not value:
            return "—"

        # ISO 8601: отрезаем дату и микросекунды.
        if "T" in value:
            time_part = value.split("T", 1)[1]
            return time_part.split(".")[0].split("+")[0]

        return value

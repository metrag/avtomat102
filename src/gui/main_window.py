"""Главное окно тренажёра стрельбы по БПЛА."""

import logging
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.gui.calibration_dialog import CalibrationDialog
from src.utils.config import load_config

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Главное окно тренера с видеопанелью, журналом и статистикой."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Инициализация главного окна.

        Args:
            parent: Родительский виджет.
        """
        super().__init__(parent)
        self.setWindowTitle("Тренажёр стрельбы по БПЛА")
        self.resize(1200, 800)

        self._config = load_config()
        self._session_started = False
        self._hits = 0
        self._misses = 0

        self._build_ui()
        self._connect_actions()

    def _build_ui(self) -> None:
        """Создаёт виджеты и компоновку главного окна."""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)

        # Левая панель: видео + управление.
        left_panel = QVBoxLayout()
        self._video_label = QLabel("Видеопоток не подключён")
        self._video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._video_label.setMinimumSize(640, 480)
        self._video_label.setStyleSheet("background-color: #1a1a1a; color: #ffffff;")
        left_panel.addWidget(self._video_label)

        control_group = QGroupBox("Управление")
        control_layout = QHBoxLayout(control_group)

        self._calibrate_button = QPushButton("F1 Калибровка прицела")
        self._start_button = QPushButton("F2 Начать занятие")
        self._finish_button = QPushButton("F3 Завершить")
        self._finish_button.setEnabled(False)

        control_layout.addWidget(self._calibrate_button)
        control_layout.addWidget(self._start_button)
        control_layout.addWidget(self._finish_button)
        left_panel.addWidget(control_group)

        main_layout.addLayout(left_panel, stretch=2)

        # Правая панель: журнал + статистика.
        right_panel = QVBoxLayout()

        journal_group = QGroupBox("Журнал выстрелов")
        journal_layout = QVBoxLayout(journal_group)
        self._shots_table = QTableWidget(0, 4)
        self._shots_table.setHorizontalHeaderLabels(
            ["№", "Время", "Результат", "Координаты"]
        )
        self._shots_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        journal_layout.addWidget(self._shots_table)
        right_panel.addWidget(journal_group, stretch=2)

        stats_group = QGroupBox("Статистика")
        stats_layout = QVBoxLayout(stats_group)
        self._hits_label = QLabel("Попадания: 0")
        self._misses_label = QLabel("Промахи: 0")
        self._accuracy_label = QLabel("Точность: —")
        stats_layout.addWidget(self._hits_label)
        stats_layout.addWidget(self._misses_label)
        stats_layout.addWidget(self._accuracy_label)
        right_panel.addWidget(stats_group, stretch=1)

        main_layout.addLayout(right_panel, stretch=1)

    def _connect_actions(self) -> None:
        """Подключает горячие клавиши и слоты кнопок."""
        calibrate_action = QAction("Калибровка", self)
        calibrate_action.setShortcut(QKeySequence("F1"))
        calibrate_action.triggered.connect(self.on_calibrate)
        self.addAction(calibrate_action)
        self._calibrate_button.clicked.connect(self.on_calibrate)

        start_action = QAction("Начать занятие", self)
        start_action.setShortcut(QKeySequence("F2"))
        start_action.triggered.connect(self.on_start_session)
        self.addAction(start_action)
        self._start_button.clicked.connect(self.on_start_session)

        finish_action = QAction("Завершить", self)
        finish_action.setShortcut(QKeySequence("F3"))
        finish_action.triggered.connect(self.on_finish_session)
        self.addAction(finish_action)
        self._finish_button.clicked.connect(self.on_finish_session)

    def on_calibrate(self) -> None:
        """Открывает диалог калибровки прицела."""
        logger.info("Opening calibration dialog")
        dialog = CalibrationDialog(self)
        dialog.exec()

    def on_start_session(self) -> None:
        """Начинает новое тренировочное занятие."""
        logger.info("Starting training session")
        self._session_started = True
        self._hits = 0
        self._misses = 0
        self._shots_table.setRowCount(0)
        self._update_stats()

        self._start_button.setEnabled(False)
        self._finish_button.setEnabled(True)
        self._video_label.setText("Занятие начато. Ожидание кадров...")

    def on_finish_session(self) -> None:
        """Завершает текущее тренировочное занятие."""
        logger.info("Finishing training session")
        self._session_started = False
        self._start_button.setEnabled(True)
        self._finish_button.setEnabled(False)
        self._video_label.setText("Занятие завершено")

    def on_shot(self, hit: bool, coordinates: tuple[int, int]) -> None:
        """Добавляет запись о выстреле в журнал.

        Args:
            hit: Флаг попадания.
            coordinates: Координаты точки прицеливания (x, y).
        """
        if not self._session_started:
            logger.warning("Shot received while session is not active")
            return

        if hit:
            self._hits += 1
            result = "Попадание"
        else:
            self._misses += 1
            result = "Промах"

        row = self._shots_table.rowCount()
        self._shots_table.insertRow(row)
        self._shots_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        self._shots_table.setItem(
            row, 1, QTableWidgetItem(datetime.now().strftime("%H:%M:%S.%f")[:-3])
        )
        self._shots_table.setItem(row, 2, QTableWidgetItem(result))
        self._shots_table.setItem(
            row, 3, QTableWidgetItem(f"{coordinates[0]}, {coordinates[1]}")
        )

        self._update_stats()

    def _update_stats(self) -> None:
        """Обновляет панель статистики."""
        total = self._hits + self._misses
        accuracy = (self._hits / total * 100.0) if total > 0 else 0.0

        self._hits_label.setText(f"Попадания: {self._hits}")
        self._misses_label.setText(f"Промахи: {self._misses}")
        self._accuracy_label.setText(f"Точность: {accuracy:.1f}%")

    def closeEvent(self, event) -> None:
        """Обрабатывает закрытие окна.

        Args:
            event: Событие закрытия.
        """
        logger.info("Main window is closing")
        if self._session_started:
            self.on_finish_session()
        event.accept()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

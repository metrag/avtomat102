"""Главное окно тренажёра стрельбы по БПЛА."""

import logging
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
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
from src.gui.stats_dialog import StatsDialog
from src.storage.journal import ShotJournal
from src.utils.config import load_config

logger = logging.getLogger(__name__)

# Соотношение сторон видеопотока.
_VIDEO_ASPECT_RATIO = 4 / 3


class _AspectRatioLabel(QLabel):
    """QLabel, сохраняющий заданное соотношение сторон pixmap при ресайзе.

    Pixmap масштабируется с сохранением пропорий и центрируется внутри виджета.
    """

    def __init__(self, aspect_ratio: float, parent: QWidget | None = None) -> None:
        """Инициализация виджета видео.

        Args:
            aspect_ratio: Целевое соотношение сторон (ширина / высота).
            parent: Родительский виджет.
        """
        super().__init__(parent)
        self._aspect_ratio = aspect_ratio
        self._original_pixmap: QPixmap | None = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(640, 480)

    def setPixmap(self, pixmap: QPixmap) -> None:
        """Устанавливает исходный pixmap с масштабированием.

        Args:
            pixmap: Новый кадр видеопотока.
        """
        self._original_pixmap = pixmap
        self._fit_pixmap()

    def resizeEvent(self, event) -> None:
        """Обрабатывает изменение размера виджета.

        Args:
            event: Событие изменения размера.
        """
        super().resizeEvent(event)
        self._fit_pixmap()

    def _fit_pixmap(self) -> None:
        """Масштабирует pixmap под текущий размер с сохранением пропорий."""
        if self._original_pixmap is None or self._original_pixmap.isNull():
            return

        label_width = self.width()
        label_height = self.height()
        if label_width <= 0 or label_height <= 0:
            return

        # Рассчитываем максимальный размер с сохранением aspect ratio.
        scaled_height = int(label_width / self._aspect_ratio)
        if scaled_height > label_height:
            scaled_width = int(label_height * self._aspect_ratio)
            scaled_height = label_height
        else:
            scaled_width = label_width

        if scaled_width <= 0 or scaled_height <= 0:
            return

        scaled = self._original_pixmap.scaled(
            scaled_width,
            scaled_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        super().setPixmap(scaled)


class MainWindow(QMainWindow):
    """Главное окно тренера с видеопанелью, журналом и статистикой."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Инициализация главного окна.

        Args:
            parent: Родительский виджет.
        """
        super().__init__(parent)
        self.setWindowTitle("Тренажёр стрельбы по БПЛА")
        self.resize(1440, 900)
        self.setMinimumSize(1024, 700)

        self._config = load_config()
        self._journal = ShotJournal()
        self._session_id: int | None = None
        self._session_started = False
        self._hits = 0
        self._misses = 0

        self._build_ui()
        self._connect_actions()
        self._update_session_status()

    def _build_ui(self) -> None:
        """Создаёт виджеты и компоновку главного окна."""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # Верхняя зона: видео слева, правая колонка фиксированной ширины.
        top_layout = QHBoxLayout()
        top_layout.setSpacing(12)

        self._video_label = _AspectRatioLabel(_VIDEO_ASPECT_RATIO, central)
        self._video_label.setText("Видеопоток не подключён")
        self._video_label.setStyleSheet("background-color: #1a1a1a; color: #ffffff;")
        top_layout.addWidget(self._video_label, stretch=1)

        right_column = self._build_right_column()
        top_layout.addLayout(right_column)

        main_layout.addLayout(top_layout, stretch=3)

        # Нижняя зона: журнал выстрелов.
        journal_group = QGroupBox("Журнал выстрелов")
        journal_layout = QVBoxLayout(journal_group)

        self._shots_table = QTableWidget(0, 4)
        self._shots_table.setHorizontalHeaderLabels(
            ["№", "Время", "Результат", "Координаты"]
        )
        self._shots_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._shots_table.setColumnWidth(0, 60)
        journal_layout.addWidget(self._shots_table)
        main_layout.addWidget(journal_group, stretch=1)

    def _build_right_column(self) -> QVBoxLayout:
        """Создаёт правую колонку управления и статистики.

        Returns:
            Компоновка правой колонки фиксированной ширины.
        """
        right_column = QVBoxLayout()
        right_column.setSpacing(12)
        right_column.setContentsMargins(0, 0, 0, 0)

        # Фиксируем ширину колонки через контейнер.
        right_container = QFrame()
        right_container.setFixedWidth(360)
        right_container.setFrameShape(QFrame.Shape.StyledPanel)
        right_layout = QVBoxLayout(right_container)
        right_layout.setSpacing(12)
        right_layout.setContentsMargins(12, 12, 12, 12)

        # Панель управления.
        control_group = QGroupBox("Управление")
        control_layout = QVBoxLayout(control_group)

        self._calibrate_button = QPushButton("⚙ F1 Калибровка прицела")
        self._start_button = QPushButton("▶ F2 Начать занятие")
        self._finish_button = QPushButton("■ F3 Завершить")
        self._stats_button = QPushButton("📊 F4 Статистика")
        self._finish_button.setEnabled(False)

        control_layout.addWidget(self._calibrate_button)
        control_layout.addWidget(self._start_button)
        control_layout.addWidget(self._finish_button)
        control_layout.addWidget(self._stats_button)

        # Статус-индикатор сессии.
        self._status_label = QLabel("Сессия: неактивна")
        self._status_label.setObjectName("status_inactive")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        control_layout.addWidget(self._status_label)

        right_layout.addWidget(control_group)

        # Блок статистики.
        stats_group = QGroupBox("Статистика")
        stats_layout = QVBoxLayout(stats_group)

        self._hits_label = QLabel("Попадания: 0")
        self._misses_label = QLabel("Промахи: 0")
        self._accuracy_label = QLabel("Точность: —")
        stats_layout.addWidget(self._hits_label)
        stats_layout.addWidget(self._misses_label)
        stats_layout.addWidget(self._accuracy_label)

        right_layout.addWidget(stats_group)
        right_layout.addStretch()

        right_column.addWidget(right_container)
        return right_column

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

        stats_action = QAction("Статистика", self)
        stats_action.setShortcut(QKeySequence("F4"))
        stats_action.triggered.connect(self.on_stats)
        self.addAction(stats_action)
        self._stats_button.clicked.connect(self.on_stats)

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

        try:
            self._session_id = self._journal.start_session()
        except Exception as exc:
            logger.exception("Failed to start session in journal: %s", exc)
            self._session_id = None

        self._update_stats()
        self._update_session_status()

        self._start_button.setEnabled(False)
        self._finish_button.setEnabled(True)
        self._video_label.setText("Занятие начато. Ожидание кадров...")

    def on_finish_session(self) -> None:
        """Завершает текущее тренировочное занятие."""
        logger.info("Finishing training session")
        self._session_started = False

        if self._session_id is not None:
            try:
                self._journal.finish_session(self._session_id)
            except Exception as exc:
                logger.exception("Failed to finish session in journal: %s", exc)
            finally:
                self._session_id = None

        self._start_button.setEnabled(True)
        self._finish_button.setEnabled(False)
        self._video_label.setText("Занятие завершено")
        self._update_session_status()

    def on_stats(self) -> None:
        """Открывает диалог статистики последней сессии."""
        logger.info("Opening stats dialog")
        dialog = StatsDialog(journal=self._journal, parent=self)
        dialog.exec()

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
            result_color = Qt.GlobalColor.green
        else:
            self._misses += 1
            result = "Промах"
            result_color = Qt.GlobalColor.red

        timestamp = datetime.now()
        row = self._shots_table.rowCount()
        self._shots_table.insertRow(row)

        number_item = QTableWidgetItem(str(row + 1))
        number_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._shots_table.setItem(row, 0, number_item)

        time_item = QTableWidgetItem(timestamp.strftime("%H:%M:%S.%f")[:-3])
        self._shots_table.setItem(row, 1, time_item)

        result_item = QTableWidgetItem(result)
        result_item.setForeground(result_color)
        self._shots_table.setItem(row, 2, result_item)

        coords_item = QTableWidgetItem(f"{coordinates[0]}, {coordinates[1]}")
        self._shots_table.setItem(row, 3, coords_item)

        if self._session_id is not None:
            try:
                self._journal.log_shot(
                    session_id=self._session_id,
                    hit=hit,
                    aim=coordinates,
                )
            except Exception as exc:
                logger.exception("Failed to log shot in journal: %s", exc)

        self._update_stats()

    def set_video_frame(self, pixmap: QPixmap) -> None:
        """Устанавливает текущий кадр видеопотока.

        Args:
            pixmap: Кадр видеопотока.
        """
        self._video_label.setPixmap(pixmap)

    def _update_stats(self) -> None:
        """Обновляет панель статистики."""
        total = self._hits + self._misses
        accuracy = (self._hits / total * 100.0) if total > 0 else 0.0

        self._hits_label.setText(f"Попадания: {self._hits}")
        self._misses_label.setText(f"Промахи: {self._misses}")
        self._accuracy_label.setText(f"Точность: {accuracy:.1f}%")

    def _update_session_status(self) -> None:
        """Обновляет индикатор состояния сессии."""
        if self._session_started:
            self._status_label.setText("Сессия: активна")
            self._status_label.setObjectName("status_active")
        else:
            self._status_label.setText("Сессия: неактивна")
            self._status_label.setObjectName("status_inactive")
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)

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

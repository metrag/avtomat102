# Python Code Style Guide

## Основы (PEP 8)

### Форматирование
- **Отступы:** 4 пробела (не табы)
- **Максимальная длина строки:** 100 символов (для читаемости на широких мониторах)
- **Пустые строки:**
  - 2 пустые строки между классами и функциями верхнего уровня
  - 1 пустая строка между методами класса
  - 1 пустая строка для разделения логических блоков внутри функций

### Именование
- **Модули:** `lowercase_with_underscores.py` (например, `video_receiver.py`, `detection_engine.py`)
- **Классы:** `CamelCase` (например, `VideoReceiver`, `DetectionEngine`, `TrainerGUI`)
- **Функции и методы:** `lowercase_with_underscores` (например, `process_frame`, `calculate_lead`)
- **Константы:** `UPPERCASE_WITH_UNDERSCORES` (например, `MAX_BUFFER_SIZE`, `DEFAULT_PORT`)
- **Переменные:** `lowercase_with_underscores` (например, `frame_count`, `drone_bbox`)
- **Приватные атрибуты:** `_leading_underscore` (например, `_video_buffer`, `_detection_model`)

### Импорты
```python
# 1. Стандартная библиотека
import sys
import json
import socket
from datetime import datetime
from pathlib import Path

# 2. Сторонние библиотеки
import cv2
import numpy as np
from PyQt6.QtWidgets import QMainWindow, QLabel
from ultralytics import YOLO

# 3. Локальные модули
from .video_receiver import VideoReceiver
from .detection_engine import DetectionEngine
```

- Группируйте импорты по категориям (стандартная библиотека, сторонние, локальные)
- Используйте абсолютные импорты (`from app.module import Class`)
- Избегайте `from module import *`

## Структура проекта

```
trainer_project/
├── main.py                    # Точка входа
├── config/
│   └── settings.json          # Конфигурация
├── src/
│   ├── __init__.py
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py     # Главное окно
│   │   ├── video_widget.py    # Виджет видео
│   │   └── calibration_dialog.py
│   ├── network/
│   │   ├── __init__.py
│   │   ├── udp_receiver.py    # UDP-приёмник
│   │   └── protocol.py        # Формат пакетов
│   ├── detection/
│   │   ├── __init__.py
│   │   ├── yolo_detector.py   # YOLOv8 детекция
│   │   └── hit_detection.py   # Анализ попадания
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── database.py        # SQLite операции
│   │   └── exporter.py        # Экспорт в CSV
│   └── utils/
│       ├── __init__.py
│       ├── image_processing.py
│       └── math_utils.py      # Расчёт упреждения
├── data/
│   ├── screenshots/
│   └── exports/
├── tests/
│   ├── test_detection.py
│   ├── test_network.py
│   └── test_gui.py
└── requirements.txt
```

## Классы и ООП

### Структура класса
```python
class DetectionEngine:
    """Движок детекции БПЛА с использованием YOLOv8.
    
    Attributes:
        model: Модель YOLOv8 для детекции и сегментации
        confidence_threshold: Порог уверенности (0.0-1.0)
        device: Устройство для инференса ('cuda' или 'cpu')
    """
    
    # Константы класса
    DEFAULT_CONFIDENCE = 0.5
    MAX_BUFFER_SIZE = 100
    
    def __init__(self, model_path: str, device: str = 'cuda'):
        """Инициализация движка детекции.
        
        Args:
            model_path: Путь к файлу модели (.pt)
            device: Устройство для инференса
        """
        self._model = YOLO(model_path)
        self._device = device
        self._buffer = []
    
    def detect(self, frame: np.ndarray) -> list[dict]:
        """Детекция БПЛА на кадре.
        
        Args:
            frame: Входный кадр (BGR формат)
            
        Returns:
            Список обнаруженных объектов с координатами и масками
            
        Raises:
            ValueError: Если кадр пустой или имеет неверный формат
        """
        if frame is None or frame.size == 0:
            raise ValueError("Empty frame provided")
        
        # ... implementation
```

### Принципы
- **Один класс — одна ответственность** (SRP)
- **Используйте type hints** для всех публичных методов
- **Docstrings** в формате Google для всех публичных классов и методов
- **Приватные методы** начинаются с `_` (например, `_preprocess_frame`)
- **Избегайте множественного наследования** (используйте миксины с осторожностью)

## Функции

### Структура функции
```python
def calculate_lead(
    drone_velocity: tuple[float, float],
    distance: float,
    bullet_speed: float = 900.0
) -> tuple[float, float]:
    """Расчёт упреждения для стрельбы по движущемуся БПЛА.
    
    Args:
        drone_velocity: Скорость дрона (vx, vy) в м/с
        distance: Дистанция до цели в метрах
        bullet_speed: Скорость пули в м/с (по умолчанию 900 м/с)
        
    Returns:
        Смещение прицела (dx, dy) в метрах
        
    Example:
        >>> lead = calculate_lead((5.0, 0.0), 100.0)
        >>> print(f"Lead: {lead[0]:.2f} м")
        Lead: 0.56 м
    """
    flight_time = distance / bullet_speed
    lead_x = drone_velocity[0] * flight_time
    lead_y = drone_velocity[1] * flight_time
    return (lead_x, lead_y)
```

### Принципы
- **Максимальная длина функции:** 50 строк (рекомендуется)
- **Одна функция — одно действие**
- **Избегайте более 3-4 параметров** (используйте dataclass для сложных структур)
- **Используйте dataclass** для передачи связанных данных:
  ```python
  from dataclasses import dataclass
  
  @dataclass
  class DetectionResult:
      bbox: tuple[int, int, int, int]
      mask: np.ndarray
      confidence: float
      class_id: int
  ```

## Обработка ошибок

### try/except
```python
# Хорошо
try:
    frame = self._decode_frame(data)
    detections = self._model.detect(frame)
except cv2.error as e:
    logger.error(f"Frame decoding failed: {e}")
    raise ProcessingError("Failed to decode video frame") from e
except Exception as e:
    logger.exception(f"Unexpected error in detection: {e}")
    raise

# Плохо
try:
    frame = self._decode_frame(data)
    detections = self._model.detect(frame)
except:  # Никогда не используйте bare except
    pass  # Никогда не игнорируйте ошибки
```

### Принципы
- **Всегда логируйте исключения** с контекстом
- **Используйте специфичные исключения** (не `Exception` для всего)
- **Создавайте пользовательские исключения** для домена:
  ```python
  class TrainerError(Exception):
      """Базовое исключение для тренажёра."""
      pass
  
  class NetworkError(TrainerError):
      """Ошибка сети."""
      pass
  
  class DetectionError(TrainerError):
      """Ошибка детекции."""
      pass
  ```
- **Используйте `raise ... from e`** для сохранения цепочки исключений

## Конкурентность и асинхронность

### PyQt6 Signals/Slots
```python
class VideoReceiver(QObject):
    frame_received = pyqtSignal(np.ndarray)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, port: int = 5000):
        super().__init__()
        self._port = port
        self._running = False
    
    def start(self):
        """Запуск приёма видео в отдельном потоке."""
        self._running = True
        self._thread = threading.Thread(target=self._receive_loop, daemon=True)
        self._thread.start()
    
    def _receive_loop(self):
        """Цикл приёма кадров (выполняется в отдельном потоке)."""
        while self._running:
            try:
                frame = self._receive_frame()
                self.frame_received.emit(frame)
            except Exception as e:
                self.error_occurred.emit(str(e))
```

### Принципы
- **Никогда не блокируйте GUI поток** (используйте QThread или threading)
- **Используйте сигналы/слоты** для коммуникации между потоками
- **Избегайте глобального состояния** (используйте dependency injection)

## Работа с изображениями (OpenCV/NumPy)

### Формат изображений
```python
# OpenCV использует BGR формат
frame_bgr = cv2.imread('image.jpg')

# PyQt6 ожидает RGB
frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

# YOLOv8 принимает RGB или BGR (проверяйте документацию)
results = model(frame_rgb)  # или frame_bgr
```

### Принципы
- **Всегда указывайте цветовое пространство** в комментариях
- **Используйте NumPy векторизацию** вместо циклов:
  ```python
  # Плохо
  for i in range(len(points)):
      points[i] = points[i] * scale
  
  # Хорошо
  points *= scale
  ```
- **Избегайте копий массивов** без необходимости:
  ```python
  # Плохо (создаёт копию)
  frame_copy = frame.copy()
  processed = self._process(frame_copy)
  
  # Хорошо (если не нужно изменять оригинал)
  processed = self._process(frame)
  ```

## Конфигурация и константы

### settings.json
```json
{
  "network": {
    "video_port": 5000,
    "trigger_port": 5001,
    "buffer_size": 65536
  },
  "detection": {
    "model_path": "models/yolov8s-seg.pt",
    "confidence_threshold": 0.5,
    "device": "cuda"
  },
  "calibration": {
    "offset_x": 0,
    "offset_y": 0
  },
  "lead": {
    "bullet_speed": 900.0,
    "enabled": true
  }
}
```

### Загрузка конфигурации
```python
import json
from pathlib import Path

def load_config(config_path: str = "config/settings.json") -> dict:
    """Загрузка конфигурации из JSON файла."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
```

## Логирование

### Настройка logging
```python
import logging

def setup_logging(level: str = "INFO") -> None:
    """Настройка логирования для приложения."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler('trainer.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

# Использование
logger = logging.getLogger(__name__)
logger.info("Application started")
logger.error(f"Failed to connect: {error}")
logger.debug(f"Frame received: shape={frame.shape}")
```

### Принципы
- **Используйте `logging`** вместо `print()`
- **Указывайте контекст** в сообщениях (имя модуля, ID сессии)
- **Разные уровни логирования:**
  - `DEBUG`: Детальная информация для отладки
  - `INFO`: Основные события (старт, остановка, подключение)
  - `WARNING`: Потенциальные проблемы
  - `ERROR`: Ошибки, но приложение продолжает работать
  - `CRITICAL`: Критические ошибки, приложение не может продолжать

## Тестирование

### Структура теста
```python
import pytest
import numpy as np
from src.detection.hit_detection import HitDetector

class TestHitDetector:
    """Тесты для детектора попаданий."""
    
    @pytest.fixture
    def detector(self):
        """Фикстура для создания детектора."""
        return HitDetector(confidence_threshold=0.5)
    
    def test_hit_inside_mask(self, detector):
        """Тест попадания внутрь маски."""
        aim_point = (100, 100)
        mask = np.zeros((200, 200), dtype=np.uint8)
        mask[50:150, 50:150] = 1  # Квадратная маска
        
        result = detector.check_hit(aim_point, mask)
        assert result is True
    
    def test_miss_outside_mask(self, detector):
        """Тест промаха вне маски."""
        aim_point = (180, 180)
        mask = np.zeros((200, 200), dtype=np.uint8)
        mask[50:150, 50:150] = 1
        
        result = detector.check_hit(aim_point, mask)
        assert result is False
```

### Принципы
- **Имя теста:** `test_<что_тестируем>_<условие>` (например, `test_hit_inside_mask`)
- **Используйте fixtures** для переиспользуемого кода
- **Один тест — одна проверка** (избегайте множественных `assert`)
- **Покрытие кода:** ≥80% для критичных модулей (детекция, сеть)

## Комментарии и документация

### Когда комментировать
- **Сложная бизнес-логика** (расчёт упреждения, алгоритм засчёта)
- **Нестандартные решения** (обход ограничений библиотеки)
- **Публичные API** (docstrings для всех публичных классов и методов)
- **TODO/FIXME** для будущих улучшений

### Формат комментариев
```python
# Хорошо
# Расчёт времени полёта пули до цели (линейная модель)
flight_time = distance / bullet_speed

# Упреждение: смещение прицела на время полёта пули
lead_x = drone_velocity[0] * flight_time

# Плохо
# Вычисляем время
t = d / v

# Считаем упреждение
lx = vx * t
```

### Docstrings
```python
def process_trigger_frame(
    frame: np.ndarray,
    calibration: CalibrationData,
    lead_settings: LeadSettings | None = None
) -> ShotResult:
    """Обработка кадра при нажатии триггера.
    
    Выполняет детекцию БПЛА, применяет калибровку прицела,
    рассчитывает упреждение (если включено) и определяет
    факт попадания.
    
    Args:
        frame: Кадр с камеры (RGB формат, shape: HxWx3)
        calibration: Данные калибровки прицела
        lead_settings: Настройки упреждения (None если выключено)
        
    Returns:
        ShotResult с результатом выстрела:
        - hit: bool — факт попадания
        - aim_point: tuple[int, int] — точка прицеливания
        - drone_bbox: tuple[int, int, int, int] | None — рамка дрона
        - confidence: float — уверенность детекции
        
    Raises:
        DetectionError: Если не удалось выполнить детекцию
        ValueError: Если кадр имеет неверный формат
        
    Example:
        >>> result = process_trigger_frame(frame, calibration)
        >>> if result.hit:
        ...     print("Попадание!")
    """
```

## Специфичные рекомендации для проекта

### PyQt6
- **Используйте Designer** для сложных форм (сохраняйте в `.ui` файлы)
- **Разделяйте логику и представление** (MVC/MVP паттерн)
- **Не создавайте виджеты в цикле** (используйте layouts)

### UDP Networking
- **Всегда закрывайте сокеты** в `finally` блоке
- **Используйте неблокирующий режим** для приёма видео
- **Обрабатывайте потерю пакетов** (проверка контрольных сумм)

### YOLOv8
- **Загружайте модель один раз** при старте приложения
- **Используйте GPU** если доступен (проверка `torch.cuda.is_available()`)
- **Кэшируйте результаты** для повторных запросов (опционально)

### База данных
- **Используйте контекстные менеджеры** для соединений:
  ```python
  with sqlite3.connect('trainer.db') as conn:
      cursor = conn.execute(query, params)
  ```
- **Транзакции** для групповых операций (вставка серии выстрелов)
- **Индексы** для часто запрашиваемых полей (session_id, timestamp)

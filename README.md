# Тренажёр стрельбы по БПЛА

Интерактивный каркас тренажёра для обучения стрельбе по движущимся БПЛА.
Детекция цели выполняется на ПК с помощью YOLOv8s-seg, интерфейс реализован
на PyQt6, связь с камерой/триггером — по UDP.

## Структура проекта

```
.
├── main.py                     # Точка входа
├── requirements.txt            # Зависимости
├── config/
│   └── settings.json           # Порты, путь к модели, настройки
├── src/
│   ├── gui/                    # PyQt6 интерфейс
│   │   ├── main_window.py
│   │   └── calibration_dialog.py
│   ├── network/                # UDP-приёмник и эмуляция камеры
│   │   ├── udp_receiver.py
│   │   └── mock_camera.py
│   ├── detection/              # Обёртка YOLOv8s-seg
│   │   └── detector.py
│   ├── analysis/               # Чистая логика попаданий и упреждения
│   │   ├── hit_checker.py
│   │   └── lead.py
│   ├── storage/                # SQLite-журнал
│   │   └── journal.py
│   └── utils/                  # Утилиты
│       └── config.py
├── tests/                      # Pytest-тесты
│   ├── test_hit_checker.py
│   └── test_lead.py
└── data/
    ├── calibration/            # Файлы калибровки
    ├── logs/                   # Журнал БД и логи
    └── models/                 # Веса YOLO
```

## Запуск

```cmd
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python main.py
```

### Горячие клавиши главного окна

- **F1** — Калибровка прицела
- **F2** — Начать занятие
- **F3** — Завершить занятие

## Тестирование

```cmd
python -m pytest tests/ -q
```

## Примечания

- Веса модели (`data/models/yolov8s-seg.pt`) в репозиторий не входят.
- Код платы MaixCAM находится вне scope данного каркаса.

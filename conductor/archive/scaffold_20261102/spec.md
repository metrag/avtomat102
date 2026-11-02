# Спецификация: Каркас проекта (структура, GUI, сеть, окружение)

## Обзор

Создать каркас приложения тренажёра стрельбы по БПЛА: структура каталогов, базовый PyQt6 GUI для тренера, UDP-приёмник с заглушкой камеры, окружение разработки. Код платы MaixCAM — вне scope.

## Функциональные требования

1. **Структура**: src/{gui,network,detection,analysis,storage,utils}, tests/, config/, data/{calibration,logs,models}, main.py, requirements.txt, README.md, .gitignore
2. **GUI (PyQt6)**: главное окно — видеопанель (заглушка), панель управления (F1 Калибровка, F2 Начать, F3 Завершить), журнал выстрелов (QTableWidget), статистика; диалог калибровки — клик по кадру сохраняет offset в data/calibration/calibration.json
3. **Сеть**: UDP Receiver порты 5000 (видеокадры) / 5001 (триггер), датаграмма = JSON + base64 JPEG, колбэки без жёсткой привязки к PyQt; MockCamera — эмуляция потока и триггера (в т.ч. локальная отправка UDP)
4. **Детекция**: обёртка YOLOv8s-seg (load_model/detect), корректная ошибка при отсутствии модели
5. **Чистая логика**: hit_checker (точка в маске/ббоксе), lead (time_of_flight, lead_offset) — pytest-тесты без PyQt/opencv
6. **Хранение**: SQLite-журнал sessions/shots; utils/config — load/save config.json
7. **Окружение**: python -m venv .venv + pip install -r requirements.txt (best effort)

## Критерии приёмки

- Все заявленные файлы существуют, main.py синтаксически корректен
- pytest tests/ проходит
- Стиль по conductor/code_styleguides/python.md (type hints, PEP 8)

## Вне scope

Код для MaixCAM, обучение/закачка весов модели, отладка с реальной камерой.

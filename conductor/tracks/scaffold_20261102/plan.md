# План реализации: Каркас проекта

## Фаза 1: Структура проекта

- [x] Task: Каталоги src/*, tests, config, data/{calibration,logs,models} (+.gitkeep)
- [x] Task: main.py, requirements.txt, README.md, .gitignore, config/settings.json

## Фаза 2: Чистая логика (TDD)

- [x] Task: Написать tests/test_hit_checker.py, tests/test_lead.py
- [x] Task: Реализовать src/analysis/hit_checker.py, src/analysis/lead.py
- [x] Task: Запустить pytest — зелёный

## Фаза 3: Сеть

- [x] Task: src/network/udp_receiver.py (5000/5001, JSON+base64, колбэки)
- [x] Task: src/network/mock_camera.py (видео/тест-кадр, UDP-эмуляция)

## Фаза 4: GUI и модули

- [x] Task: src/gui/main_window.py (видеопанель, F1/F2/F3, журнал, статистика)
- [x] Task: src/gui/calibration_dialog.py (клик → calibration.json)
- [x] Task: src/detection/detector.py (обёртка YOLOv8s-seg)
- [x] Task: src/storage/journal.py (SQLite), src/utils/config.py

## Фаза 5: Окружение

- [x] Task: python -m venv .venv; pip install -r requirements.txt (best effort)

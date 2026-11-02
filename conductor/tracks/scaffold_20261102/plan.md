# План реализации: Каркас проекта

## Фаза 1: Структура проекта

- [ ] Task: Каталоги src/*, tests, config, data/{calibration,logs,models} (+.gitkeep)
- [ ] Task: main.py, requirements.txt, README.md, .gitignore, config/settings.json

## Фаза 2: Чистая логика (TDD)

- [ ] Task: Написать tests/test_hit_checker.py, tests/test_lead.py
- [ ] Task: Реализовать src/analysis/hit_checker.py, src/analysis/lead.py
- [ ] Task: Запустить pytest — зелёный

## Фаза 3: Сеть

- [ ] Task: src/network/udp_receiver.py (5000/5001, JSON+base64, колбэки)
- [ ] Task: src/network/mock_camera.py (видео/тест-кадр, UDP-эмуляция)

## Фаза 4: GUI и модули

- [ ] Task: src/gui/main_window.py (видеопанель, F1/F2/F3, журнал, статистика)
- [ ] Task: src/gui/calibration_dialog.py (клик → calibration.json)
- [ ] Task: src/detection/detector.py (обёртка YOLOv8s-seg)
- [ ] Task: src/storage/journal.py (SQLite), src/utils/config.py

## Фаза 5: Окружение

- [ ] Task: python -m venv .venv; pip install -r requirements.txt (best effort)

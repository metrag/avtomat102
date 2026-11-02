# План: Экспорт отчёта сессии

## Фаза 1: Логика экспорта

- [x] Task: Тесты export_report (CSV, TXT, ошибки, имя файла)
- [x] Task: src/storage/report.py — сборка данных и запись CSV/TXT в data/reports/

## Фаза 2: Интерфейс

- [x] Task: Кнопки «Экспорт CSV»/«Экспорт TXT» в StatsDialog + сообщение с путём
- [x] Task: .gitignore для data/reports/, config storage.reports_dir

## Фаза 3: Проверка

- [x] Task: pytest зелёный (39 passed); импорты OK; ручной запуск — подтверждение пользователя

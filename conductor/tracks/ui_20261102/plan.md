# План: Проработка интерфейса и стиля

## Фаза 1: Тема и стили

- [x] Task: Написать тесты для src/analysis/session_stats.py (pure: сводка из списка выстрелов)
- [x] Task: Создать src/gui/styles.qss (палитра #1E1E1E/#00FF41, кнопки, таблицы)
- [x] Task: src/analysis/session_stats.py + подключение QSS в main.py

## Фаза 2: Раскладка главного окна

- [x] Task: Переработать src/gui/main_window.py: видео слева, колонка 360px справа, журнал снизу; 1440×900/min 1024×700; size policies

## Фаза 3: Иконки и индикация

- [x] Task: Иконки F1/F2/F3 (QIcon из ресурсов/Unicode), статус-индикатор сессии
- [x] Task: Окраска строк журнала (hit/miss)

## Фаза 4: Экран статистики

- [x] Task: src/gui/stats_dialog.py — сводка сессии из journal.db через session_stats
- [x] Task: Кнопка/клавиша открытия статистики в главном окне

## Фаза 5: Проверка

- [x] Task: pytest — зелёный; ручной запуск main.py (подтверждение пользователя)

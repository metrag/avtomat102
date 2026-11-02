"""Точка входа в интерактивный тренажёр стрельбы по БПЛА.

Приложение запускает PyQt6-интерфейс тренера. Если зависимости GUI
не установлены, на верхнем уровне выводится понятное сообщение,
без трассировки стека.
"""

import logging
import sys
from pathlib import Path

# Настраиваем логирование до импорта GUI, чтобы ошибки импорта тоже попадали в лог.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('trainer.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def main() -> int:
    """Запуск приложения тренажёра.

    Returns:
        Код возврата приложения (0 — успех).
    """
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError as exc:
        message = (
            "Для запуска тренажёра необходимы зависимости GUI.\n"
            "Установите их в виртуальное окружение:\n"
            "  python -m venv .venv\n"
            "  .venv\\Scripts\\python -m pip install -r requirements.txt\n"
        )
        logger.error(message)
        print(message, file=sys.stderr)
        return 1

    from src.gui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName('Тренажёр стрельбы по БПЛА')
    app.setApplicationVersion('0.1.0')

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == '__main__':
    sys.exit(main())

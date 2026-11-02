"""Загрузка и сохранение конфигурации приложения."""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path("config/settings.json")


def load_config(config_path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """Загружает конфигурацию из JSON-файла.

    Args:
        config_path: Путь к файлу настроек.

    Returns:
        Словарь с конфигурацией приложения.

    Raises:
        FileNotFoundError: Если файл не найден.
        json.JSONDecodeError: Если файл содержит некорректный JSON.
    """
    path = Path(config_path)
    if not path.exists():
        logger.error("Config file not found: %s", path)
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        config = json.load(file)

    logger.debug("Config loaded from %s", path)
    return config


def save_config(
    config: dict[str, Any],
    config_path: str | Path = DEFAULT_CONFIG_PATH,
) -> None:
    """Сохраняет конфигурацию в JSON-файл.

    Args:
        config: Словарь с конфигурацией.
        config_path: Путь к файлу настроек.
    """
    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(config, file, ensure_ascii=False, indent=2)

    logger.debug("Config saved to %s", path)

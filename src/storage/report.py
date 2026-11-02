"""Экспорт отчёта тренировочной сессии в CSV и TXT.

Формирует файл с шапкой занятия, итогами и таблицей выстрелов.
CSV пишется в UTF-8 с BOM и разделителем ';' (корректное открытие
в русском Excel); TXT — обычный UTF-8.
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from src.analysis.session_stats import summarize
from src.storage.journal import ShotJournal
from src.utils.config import load_config

logger = logging.getLogger(__name__)

DEFAULT_REPORTS_DIR = Path("data/reports")
CSV_DELIMITER = ";"
_TABLE_HEADER = ["№", "Время", "Результат", "Прицел X", "Прицел Y", "Уверенность", "Фото"]


class ReportError(Exception):
    """Ошибка формирования отчёта."""

    pass


def _safe_name(text: str) -> str:
    """Очищает строку для использования в имени файла.

    Args:
        text: Исходная строка (например, ФИО).

    Returns:
        Строка без запрещённых символов; 'сессия', если результат пуст.
    """
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", text).strip(" .")
    return cleaned or "сессия"


def _session_stamp(session: dict[str, Any]) -> str:
    """Формирует метку времени из начала сессии для имени файла.

    Args:
        session: Словарь сессии (ключ started_at).

    Returns:
        Строка вида YYYYMMDD_HHMMSS или текущее время как запасной вариант.
    """
    started = str(session.get("started_at") or "")
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})", started)
    if match:
        year, month, day, hour, minute, second = match.groups()
        return f"{year}{month}{day}_{hour}{minute}{second}"
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _format_dt(value: Any) -> str:
    """Форматирует ISO-метку времени в ЧЧ.ММ.ГГГГ ЧЧ:ММ:СС.

    Args:
        value: Метка времени или None.

    Returns:
        Отформатированная строка или '—'.
    """
    if not value:
        return "—"
    text = str(value)
    if "T" not in text:
        return text
    date_part, rest = text.split("T", 1)
    time_part = rest.split(".")[0].split("+")[0].split("Z")[0]
    if len(date_part) == 10 and date_part[4] == "-":
        date_part = f"{date_part[8:10]}.{date_part[5:7]}.{date_part[:4]}"
    return f"{date_part} {time_part}".strip()


def _format_time(value: Any) -> str:
    """Извлекает ЧЧ:ММ:СС из метки времени.

    Args:
        value: Метка времени.

    Returns:
        Время или '—'.
    """
    if not value:
        return "—"
    text = str(value)
    if "T" in text:
        return text.split("T", 1)[1].split(".")[0].split("+")[0].split("Z")[0]
    return text


def _header_pairs(
    session: dict[str, Any], stats: dict[str, Any]
) -> list[tuple[str, str]]:
    """Собирает пары «ключ;значение» для шапки отчёта.

    Args:
        session: Словарь сессии.
        stats: Сводка summarize().

    Returns:
        Список кортежей (название, значение).
    """
    return [
        ("Тренажёр стрельбы по БПЛА", "Отчёт о тренировочном занятии"),
        ("ФИО", session.get("full_name") or "—"),
        ("Звание", session.get("rank") or "—"),
        ("Учебная группа", session.get("group_no") or "—"),
        ("Режим стрельбы", session.get("mode") or "—"),
        (
            "Дистанция, м",
            str(session["distance"]) if session.get("distance") is not None else "—",
        ),
        (
            "Патроны",
            str(session["ammo"]) if session.get("ammo") is not None else "—",
        ),
        ("Начало", _format_dt(session.get("started_at"))),
        ("Конец", _format_dt(session.get("ended_at"))),
        ("Попаданий", str(stats["hits"])),
        ("Промахов", str(stats["misses"])),
        ("Точность, %", f"{stats['accuracy_percent']:.1f}"),
        (
            "Средний интервал, с",
            f"{stats['avg_interval_sec']:.2f}",
        ),
    ]


def _shot_row(index: int, shot: dict[str, Any]) -> list[str]:
    """Формирует строку таблицы выстрелов.

    Args:
        index: Порядковый номер выстрела.
        shot: Запись выстрела из БД.

    Returns:
        Список ячеек строки.
    """
    aim_x = shot.get("aim_x")
    aim_y = shot.get("aim_y")
    confidence = shot.get("confidence")
    return [
        str(index),
        _format_time(shot.get("timestamp")),
        "Попадание" if shot.get("hit") else "Промах",
        str(aim_x) if aim_x is not None else "—",
        str(aim_y) if aim_y is not None else "—",
        f"{confidence:.2f}" if confidence is not None else "—",
        shot.get("photo_path") or "—",
    ]


def _render_csv(
    session: dict[str, Any],
    shots: list[dict[str, Any]],
    stats: dict[str, Any],
) -> str:
    """Рендерит отчёт в формат CSV (разделитель ';').

    Args:
        session: Словарь сессии.
        shots: Список выстрелов.
        stats: Сводка summarize().

    Returns:
        Текст CSV.
    """
    lines = [
        f"{key}{CSV_DELIMITER}{value}" for key, value in _header_pairs(session, stats)
    ]
    lines.append("")
    lines.append(CSV_DELIMITER.join(_TABLE_HEADER))
    for index, shot in enumerate(shots, start=1):
        row = _shot_row(index, shot)
        # Экранирование кавычек и переносов.
        row = [cell.replace('"', '""') if '"' in cell else cell for cell in row]
        lines.append(CSV_DELIMITER.join(row))
    return "\r\n".join(lines) + "\r\n"


def _render_txt(
    session: dict[str, Any],
    shots: list[dict[str, Any]],
    stats: dict[str, Any],
) -> str:
    """Рендерит отчёт в читаемый TXT.

    Args:
        session: Словарь сессии.
        shots: Список выстрелов.
        stats: Сводка summarize().

    Returns:
        Текст отчёта.
    """
    width = 56
    lines = [
        "ТРЕНАЖЁР СТРЕЛЬБЫ ПО БПЛА — ОТЧЁТ".center(width),
        "=" * width,
    ]
    for key, value in _header_pairs(session, stats):
        lines.append(f"{key + ':':<24}{value}")
    lines.append("-" * width)

    header = (
        f"{'№':<4}{'Время':<10}{'Результат':<12}{'Прицел':<12}{'Фото'}"
    )
    lines.append(header)
    for index, shot in enumerate(shots, start=1):
        row = _shot_row(index, shot)
        aim = f"{row[3]},{row[4]}"
        lines.append(
            f"{row[0]:<4}{row[1]:<10}{row[2]:<12}{aim:<12}{row[6]}"
        )
    lines.append("=" * width)
    return "\n".join(lines) + "\n"


def export_report(
    journal: ShotJournal,
    session_id: int,
    out_dir: str | Path | None = None,
    fmt: str = "csv",
) -> Path:
    """Формирует и сохраняет отчёт о сессии.

    Args:
        journal: Журнал сессий.
        session_id: Идентификатор сессии.
        out_dir: Каталог отчётов. Если None — storage.reports_dir
            из конфигурации (по умолчанию data/reports).
        fmt: Формат файла — 'csv' или 'txt'.

    Returns:
        Путь к сохранённому файлу.

    Raises:
        ReportError: Неизвестный формат, сессия не найдена
            или ошибка записи файла.
    """
    if fmt not in ("csv", "txt"):
        raise ReportError(f"Неизвестный формат отчёта: {fmt}")

    sessions = {item["id"]: item for item in journal.get_sessions()}
    session = sessions.get(session_id)
    if session is None:
        raise ReportError(f"Сессия №{session_id} не найдена")

    if out_dir is None:
        config = load_config()
        out_dir = config.get("storage", {}).get("reports_dir", "data/reports")
    directory = Path(out_dir)

    shots = journal.get_shots(session_id)
    stats = summarize(shots)

    name = _safe_name(str(session.get("full_name") or "сессия"))
    stamp = _session_stamp(session)
    filename = f"Отчёт_{name}_{stamp}_s{session_id}.{fmt}"
    path = directory / filename

    if fmt == "csv":
        content = _render_csv(session, shots, stats)
        encoding = "utf-8-sig"
    else:
        content = _render_txt(session, shots, stats)
        encoding = "utf-8"

    try:
        directory.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding=encoding)
    except OSError as exc:
        raise ReportError(f"Не удалось записать файл: {path}") from exc

    logger.info("Report exported: %s", path)
    return path

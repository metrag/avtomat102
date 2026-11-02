"""Тесты экспорта отчёта сессии в CSV/TXT."""

import pytest

from src.storage.journal import ShotJournal
from src.storage.report import ReportError, export_report


def _journal_with_session(tmp_path):
    """Создаёт журнал с одной сессией и двумя выстрелами.

    Args:
        tmp_path: Временный каталог pytest.

    Returns:
        Кортеж (journal, session_id).
    """
    journal = ShotJournal(db_path=tmp_path / "j.db", shots_dir=tmp_path / "shots")
    session_id = journal.start_session(
        metadata={
            "rank": "Курсант",
            "full_name": "Иванов И.И.",
            "group_no": "631/12",
            "mode": "Автоматический",
            "distance": 100,
            "ammo": 30,
        }
    )
    journal.log_shot(session_id, hit=True, aim=(10, 20), confidence=0.9)
    journal.log_shot(session_id, hit=False, aim=(30, 40), confidence=0.7)
    return journal, session_id


def test_export_csv_creates_file(tmp_path):
    """CSV-отчёт создаётся и содержит шапку, итоги и строки выстрелов."""
    journal, session_id = _journal_with_session(tmp_path)

    path = export_report(journal, session_id, out_dir=tmp_path / "reports", fmt="csv")

    assert path.exists()
    assert path.suffix == ".csv"
    content = path.read_text(encoding="utf-8-sig")
    assert "ФИО;Иванов И.И." in content
    assert "Попаданий;1" in content
    assert "Промахов;1" in content
    assert "Точность, %;50.0" in content
    assert "Попадание" in content
    assert "Промах" in content


def test_export_csv_has_bom(tmp_path):
    """CSV начинается с BOM (корректное открытие в Excel)."""
    journal, session_id = _journal_with_session(tmp_path)

    path = export_report(journal, session_id, out_dir=tmp_path / "reports", fmt="csv")

    raw = path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")


def test_export_txt_creates_file(tmp_path):
    """TXT-отчёт создаётся и содержит данные занятия."""
    journal, session_id = _journal_with_session(tmp_path)

    path = export_report(journal, session_id, out_dir=tmp_path / "reports", fmt="txt")

    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "ФИО:" in content
    assert "Иванов И.И." in content
    assert "Попаданий:" in content
    assert "Попадание" in content


def test_export_filename_sanitized(tmp_path):
    """Запрещённые символы в ФИО не попадают в имя файла."""
    journal = ShotJournal(db_path=tmp_path / "j.db", shots_dir=tmp_path / "shots")
    session_id = journal.start_session(
        metadata={"full_name": 'Иванов/И.И.: "тест" <x>'}
    )

    path = export_report(journal, session_id, out_dir=tmp_path / "reports", fmt="csv")

    for char in '<>:"/\\|?*':
        assert char not in path.name


def test_export_missing_session_raises(tmp_path):
    """Несуществующая сессия даёт ReportError."""
    journal = ShotJournal(db_path=tmp_path / "j.db", shots_dir=tmp_path / "shots")

    with pytest.raises(ReportError):
        export_report(journal, 999, out_dir=tmp_path / "reports", fmt="csv")


def test_export_unknown_format_raises(tmp_path):
    """Неизвестный формат даёт ReportError."""
    journal, session_id = _journal_with_session(tmp_path)

    with pytest.raises(ReportError):
        export_report(journal, session_id, out_dir=tmp_path / "reports", fmt="pdf")


def test_export_session_without_shots(tmp_path):
    """Сессия без выстрелов экспортируется с нулевыми итогами."""
    journal = ShotJournal(db_path=tmp_path / "j.db", shots_dir=tmp_path / "shots")
    session_id = journal.start_session(metadata={"full_name": "Петров П.П."})

    path = export_report(journal, session_id, out_dir=tmp_path / "reports", fmt="csv")

    content = path.read_text(encoding="utf-8-sig")
    assert "Попаданий;0" in content
    assert "Точность, %;0.0" in content

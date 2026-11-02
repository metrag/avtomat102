"""Тесты журнала сессий и выстрелов: миграция схемы и фото."""

import sqlite3

import pytest

from src.storage.journal import ShotJournal, ShotJournalError


def _old_schema_db(tmp_path):
    """Создаёт БД со старой схемой (без новых колонок) с одной записью.

    Args:
        tmp_path: Временный каталог pytest.

    Returns:
        Путь к файлу БД.
    """
    db_path = tmp_path / "old.db"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                ended_at TEXT
            );
            CREATE TABLE shots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                hit INTEGER NOT NULL CHECK(hit IN (0, 1)),
                aim_x INTEGER,
                aim_y INTEGER,
                target_x INTEGER,
                target_y INTEGER,
                confidence REAL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );
            INSERT INTO sessions (started_at) VALUES ('2026-01-01T00:00:00');
            INSERT INTO shots (session_id, timestamp, hit, aim_x, aim_y)
            VALUES (1, '2026-01-01T00:00:01', 1, 10, 20);
            """
        )
    return db_path


def _journal(tmp_path):
    """Создаёт журнал во временном каталоге.

    Args:
        tmp_path: Временный каталог pytest.

    Returns:
        Экземпляр ShotJournal.
    """
    return ShotJournal(db_path=tmp_path / "j.db", shots_dir=tmp_path / "shots")


def test_migration_adds_columns(tmp_path):
    """Миграция добавляет новые колонки в старую схему."""
    db_path = _old_schema_db(tmp_path)
    ShotJournal(db_path=db_path, shots_dir=tmp_path / "shots")

    with sqlite3.connect(db_path) as conn:
        session_cols = {row[1] for row in conn.execute("PRAGMA table_info(sessions)")}
        shot_cols = {row[1] for row in conn.execute("PRAGMA table_info(shots)")}

    assert {"rank", "full_name", "group_no", "mode", "distance", "ammo"} <= session_cols
    assert "photo_path" in shot_cols


def test_migration_preserves_existing_rows(tmp_path):
    """Миграция не уничтожает существующие записи."""
    db_path = _old_schema_db(tmp_path)
    journal = ShotJournal(db_path=db_path, shots_dir=tmp_path / "shots")

    sessions = journal.get_sessions()
    shots = journal.get_shots(1)

    assert len(sessions) == 1
    assert len(shots) == 1
    assert shots[0]["hit"] == 1


def test_start_session_with_metadata(tmp_path):
    """Метаданные занятия сохраняются в sessions."""
    journal = _journal(tmp_path)

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

    sessions = journal.get_sessions()
    assert sessions[-1]["id"] == session_id
    assert sessions[-1]["full_name"] == "Иванов И.И."
    assert sessions[-1]["rank"] == "Курсант"
    assert sessions[-1]["group_no"] == "631/12"
    assert sessions[-1]["mode"] == "Автоматический"
    assert sessions[-1]["distance"] == 100
    assert sessions[-1]["ammo"] == 30


def test_start_session_without_metadata(tmp_path):
    """Сессия без метаданных создаётся, колонки пусты."""
    journal = _journal(tmp_path)

    journal.start_session()

    sessions = journal.get_sessions()
    assert len(sessions) == 1
    assert sessions[-1]["full_name"] is None
    assert sessions[-1]["distance"] is None


def test_log_shot_with_photo_path(tmp_path):
    """Путь к фото сохраняется в записи выстрела."""
    journal = _journal(tmp_path)
    session_id = journal.start_session()

    journal.log_shot(
        session_id,
        hit=True,
        aim=(1, 2),
        photo_path="data/shots/1/1.jpg",
    )

    shots = journal.get_shots(session_id)
    assert shots[0]["photo_path"] == "data/shots/1/1.jpg"


def test_save_shot_photo_writes_file(tmp_path):
    """save_shot_photo пишет файл в shots_dir/<session_id>/<shot_no>.jpg."""
    shots_dir = tmp_path / "shots"
    journal = ShotJournal(db_path=tmp_path / "j.db", shots_dir=shots_dir)
    session_id = journal.start_session()

    path = journal.save_shot_photo(session_id, 1, b"\xff\xd8fakejpeg")

    assert path == shots_dir / str(session_id) / "1.jpg"
    assert path.read_bytes() == b"\xff\xd8fakejpeg"


def test_save_shot_photo_invalid_dir_raises(tmp_path):
    """Ошибка записи файла превращается в ShotJournalError."""
    blocked = tmp_path / "blocked"
    blocked.write_bytes(b"x")  # файл на месте каталога
    journal = ShotJournal(db_path=tmp_path / "j.db", shots_dir=blocked)
    session_id = journal.start_session()

    with pytest.raises(ShotJournalError):
        journal.save_shot_photo(session_id, 1, b"data")

"""SQLite-журнал тренировочных сессий и выстрелов."""

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.utils.config import load_config

logger = logging.getLogger(__name__)


class ShotJournalError(Exception):
    """Ошибка работы с журналом выстрелов."""

    pass


class ShotJournal:
    """Журнал сессий и выстрелов на основе SQLite.

    Attributes:
        db_path: Путь к файлу базы данных.
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        shots_dir: str | Path | None = None,
    ) -> None:
        """Инициализация журнала.

        Args:
            db_path: Путь к БД. Если None — берётся из config/settings.json.
            shots_dir: Каталог для фото выстрелов. Если None — из config
                (storage.shots_dir, по умолчанию data/shots).
        """
        config = None
        if db_path is None or shots_dir is None:
            config = load_config()

        if db_path is None:
            db_path = config.get("storage", {}).get("db_path", "data/logs/journal.db")
        if shots_dir is None:
            shots_dir = config.get("storage", {}).get("shots_dir", "data/shots")

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.shots_dir = Path(shots_dir)
        self._init_db()

    def _init_db(self) -> None:
        """Создаёт таблицы sessions и shots, если они отсутствуют."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    ended_at TEXT
                );

                CREATE TABLE IF NOT EXISTS shots (
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

                CREATE INDEX IF NOT EXISTS idx_shots_session_id
                    ON shots(session_id);
                CREATE INDEX IF NOT EXISTS idx_shots_timestamp
                    ON shots(timestamp);
                """
            )
            self._migrate(conn)

    @staticmethod
    def _migrate(conn: sqlite3.Connection) -> None:
        """Добавляет недостающие колонки в существующие таблицы.

        Args:
            conn: Открытое соединение с БД.
        """
        migrations: dict[str, dict[str, str]] = {
            "sessions": {
                "rank": "TEXT",
                "full_name": "TEXT",
                "group_no": "TEXT",
                "mode": "TEXT",
                "distance": "INTEGER",
                "ammo": "INTEGER",
            },
            "shots": {
                "photo_path": "TEXT",
            },
        }
        for table, columns in migrations.items():
            existing = {
                row[1] for row in conn.execute(f"PRAGMA table_info({table})")
            }
            for name, col_type in columns.items():
                if name not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {col_type}")
                    logger.info("Migrated table %s: added column %s", table, name)
            conn.commit()

    def start_session(self, metadata: dict[str, Any] | None = None) -> int:
        """Создаёт новую сессию и возвращает её идентификатор.

        Args:
            metadata: Данные занятия: rank, full_name, group_no, mode,
                distance, ammo. Если None — соответствующие колонки пусты.

        Returns:
            Идентификатор созданной сессии.

        Raises:
            ShotJournalError: Если не удалось создать сессию.
        """
        now = datetime.now(timezone.utc).isoformat()
        meta = metadata or {}
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO sessions
                        (started_at, rank, full_name, group_no, mode, distance, ammo)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        now,
                        meta.get("rank"),
                        meta.get("full_name"),
                        meta.get("group_no"),
                        meta.get("mode"),
                        meta.get("distance"),
                        meta.get("ammo"),
                    ),
                )
                session_id = cursor.lastrowid
        except sqlite3.Error as exc:
            raise ShotJournalError("Failed to start session") from exc

        logger.info("Started session id=%s", session_id)
        return session_id

    def log_shot(
        self,
        session_id: int,
        hit: bool,
        aim: tuple[int, int],
        target: tuple[int, int] | None = None,
        confidence: float | None = None,
        photo_path: str | None = None,
    ) -> int:
        """Записывает информацию о выстреле.

        Args:
            session_id: Идентификатор сессии.
            hit: Флаг попадания.
            aim: Координаты прицеливания (x, y).
            target: Координаты цели (x, y) или None.
            confidence: Уверенность детекции.
            photo_path: Путь к сохранённому кадру выстрела или None.

        Returns:
            Идентификатор созданной записи.

        Raises:
            ShotJournalError: Если не удалось записать выстрел.
        """
        now = datetime.now(timezone.utc).isoformat()
        target_x, target_y = target if target is not None else (None, None)

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO shots
                    (session_id, timestamp, hit, aim_x, aim_y, target_x, target_y,
                     confidence, photo_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        now,
                        int(hit),
                        aim[0],
                        aim[1],
                        target_x,
                        target_y,
                        confidence,
                        photo_path,
                    ),
                )
                shot_id = cursor.lastrowid
        except sqlite3.Error as exc:
            raise ShotJournalError("Failed to log shot") from exc

        logger.info("Logged shot id=%s session=%s hit=%s", shot_id, session_id, hit)
        return shot_id

    def get_shots(self, session_id: int) -> list[dict[str, Any]]:
        """Возвращает список выстрелов для сессии.

        Args:
            session_id: Идентификатор сессии.

        Returns:
            Список словарей с полями выстрелов.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM shots WHERE session_id = ? ORDER BY id",
                (session_id,),
            )
            rows = cursor.fetchall()

        return [dict(row) for row in rows]

    def get_sessions(self) -> list[dict[str, Any]]:
        """Возвращает список всех сессий, отсортированных по времени старта.

        Returns:
            Список словарей с полями сессий.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM sessions ORDER BY started_at"
            )
            rows = cursor.fetchall()

        return [dict(row) for row in rows]

    def finish_session(self, session_id: int) -> None:
        """Завершает сессию, записывая время окончания.

        Args:
            session_id: Идентификатор сессии.

        Raises:
            ShotJournalError: Если не удалось завершить сессию.
        """
        now = datetime.now(timezone.utc).isoformat()
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE sessions SET ended_at = ? WHERE id = ?",
                    (now, session_id),
                )
        except sqlite3.Error as exc:
            raise ShotJournalError("Failed to finish session") from exc

        logger.info("Finished session id=%s", session_id)

    def save_shot_photo(
        self, session_id: int, shot_no: int, image_bytes: bytes
    ) -> Path:
        """Сохраняет кадр выстрела в shots_dir/<session_id>/<shot_no>.jpg.

        Args:
            session_id: Идентификатор сессии.
            shot_no: Порядковый номер выстрела в сессии.
            image_bytes: Содержимое JPEG-файла.

        Returns:
            Путь к сохранённому файлу.

        Raises:
            ShotJournalError: Если не удалось сохранить файл.
        """
        directory = self.shots_dir / str(session_id)
        try:
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / f"{shot_no}.jpg"
            path.write_bytes(image_bytes)
        except OSError as exc:
            raise ShotJournalError("Failed to save shot photo") from exc

        logger.info("Saved shot photo: %s", path)
        return path

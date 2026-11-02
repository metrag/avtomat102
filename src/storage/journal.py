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

    def __init__(self, db_path: str | Path | None = None) -> None:
        """Инициализация журнала.

        Args:
            db_path: Путь к БД. Если None — берётся из config/settings.json.
        """
        if db_path is None:
            config = load_config()
            db_path = config.get("storage", {}).get("db_path", "data/logs/journal.db")

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
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

    def start_session(self) -> int:
        """Создаёт новую сессию и возвращает её идентификатор.

        Returns:
            Идентификатор созданной сессии.

        Raises:
            ShotJournalError: Если не удалось создать сессию.
        """
        now = datetime.now(timezone.utc).isoformat()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "INSERT INTO sessions (started_at) VALUES (?)",
                    (now,),
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
    ) -> int:
        """Записывает информацию о выстреле.

        Args:
            session_id: Идентификатор сессии.
            hit: Флаг попадания.
            aim: Координаты прицеливания (x, y).
            target: Координаты цели (x, y) или None.
            confidence: Уверенность детекции.

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
                    (session_id, timestamp, hit, aim_x, aim_y, target_x, target_y, confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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

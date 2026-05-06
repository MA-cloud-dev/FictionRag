"""SQLite persistence for anonymous visitor usage and query history."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path

from .config import DEFAULT_VISITOR_DB_PATH, VISITOR_DAILY_QUOTA


class VisitorStore:
    def __init__(self, db_path: Path = DEFAULT_VISITOR_DB_PATH) -> None:
        self.db_path = db_path
        self._ensure_schema()

    def get_usage(self, visitor_id: str, usage_date: str | None = None) -> dict[str, int]:
        current_date = usage_date or _today()
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT count
                FROM visitor_daily_usage
                WHERE visitor_id = ? AND usage_date = ?
                """,
                (visitor_id, current_date),
            ).fetchone()
        used = int(row["count"]) if row else 0
        return {
            "quota": VISITOR_DAILY_QUOTA,
            "used": used,
            "remaining": max(VISITOR_DAILY_QUOTA - used, 0),
        }

    def has_remaining_quota(self, visitor_id: str, usage_date: str | None = None) -> bool:
        return self.get_usage(visitor_id, usage_date)["remaining"] > 0

    def increment_usage(self, visitor_id: str, usage_date: str | None = None) -> dict[str, int]:
        current_date = usage_date or _today()
        now = _now()
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO visitor_daily_usage
                        (visitor_id, usage_date, count, created_at, updated_at)
                    VALUES (?, ?, 1, ?, ?)
                    ON CONFLICT(visitor_id, usage_date) DO UPDATE SET
                        count = count + 1,
                        updated_at = excluded.updated_at
                    """,
                    (visitor_id, current_date, now, now),
                )
        return self.get_usage(visitor_id, current_date)

    def save_query(
        self,
        visitor_id: str,
        question: str,
        answer: str,
        used_custom_api_key: bool,
    ) -> None:
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO visitor_queries
                        (visitor_id, created_at, question, answer, used_custom_api_key)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (visitor_id, _now(), question, answer, int(used_custom_api_key)),
                )

    def _ensure_schema(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS visitor_daily_usage (
                        visitor_id TEXT NOT NULL,
                        usage_date TEXT NOT NULL,
                        count INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        PRIMARY KEY (visitor_id, usage_date)
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS visitor_queries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        visitor_id TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        question TEXT NOT NULL,
                        answer TEXT NOT NULL,
                        used_custom_api_key INTEGER NOT NULL DEFAULT 0
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_visitor_queries_visitor_created
                    ON visitor_queries(visitor_id, created_at)
                    """
                )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection


def _today() -> str:
    return date.today().isoformat()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

"""SQLite helpers for future storage migration."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path


class SqliteRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.database_path)

    def initialize(self, schema_version: int = 1) -> None:
        now = datetime.now().isoformat()
        with closing(self.connect()) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS app_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version INTEGER NOT NULL,
                    applied_at TEXT NOT NULL,
                    description TEXT NOT NULL
                );
                """
            )
            connection.execute(
                """
                INSERT INTO app_metadata (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                ("schema_version", str(schema_version)),
            )
            connection.execute(
                """
                INSERT INTO app_metadata (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO NOTHING
                """,
                ("initialized_at", now),
            )
            connection.execute(
                """
                INSERT INTO app_metadata (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                ("last_initialized_at", now),
            )
            connection.execute(
                """
                INSERT INTO migrations (version, applied_at, description)
                SELECT ?, ?, ?
                WHERE NOT EXISTS (
                    SELECT 1 FROM migrations WHERE version = ?
                )
                """,
                (schema_version, now, "bootstrap sqlite foundation", schema_version),
            )
            connection.commit()

    def get_schema_version(self) -> int | None:
        if not self.database_path.exists():
            return None
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT value FROM app_metadata WHERE key = ?",
                ("schema_version",),
            ).fetchone()
        if row is None:
            return None
        return int(row[0])

    def get_metadata(self) -> dict[str, str]:
        if not self.database_path.exists():
            return {}
        with closing(self.connect()) as connection:
            rows = connection.execute("SELECT key, value FROM app_metadata").fetchall()
        return {str(key): str(value) for key, value in rows}

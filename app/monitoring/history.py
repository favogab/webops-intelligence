
import sqlite3
from pathlib import Path

from app.monitoring.checker import CheckResult


class MonitoringHistory:
    def __init__(self, db_path: str | Path = "webops.db"):
        self.db_path = str(db_path)
        self._initialize_database()

    def _initialize_database(self) -> None:
        connection = sqlite3.connect(self.db_path)

        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS monitoring_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    status_code INTEGER,
                    status_category TEXT NOT NULL,
                    response_time_ms REAL,
                    checked_at TEXT NOT NULL,
                    is_healthy INTEGER NOT NULL,
                    content_type TEXT,
                    redirect_location TEXT,
                    error TEXT
                )
                """
            )
            connection.commit()
        finally:
            connection.close()

    def save_result(self, result: CheckResult) -> None:
        connection = sqlite3.connect(self.db_path)

        try:
            connection.execute(
                """
                INSERT INTO monitoring_history (
                    url,
                    status_code,
                    status_category,
                    response_time_ms,
                    checked_at,
                    is_healthy,
                    content_type,
                    redirect_location,
                    error
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.url,
                    result.status_code,
                    result.status_category,
                    result.response_time_ms,
                    result.checked_at.isoformat(),
                    int(result.is_healthy),
                    result.content_type,
                    result.redirect_location,
                    result.error,
                ),
            )
            connection.commit()
        finally:
            connection.close()

    def get_recent(self, limit: int = 100) -> list[CheckResult]:
        if limit < 1:
            raise ValueError("Limit must be at least 1")

        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row

        try:
            rows = connection.execute(
                """
                SELECT
                    url,
                    status_code,
                    status_category,
                    response_time_ms,
                    checked_at,
                    is_healthy,
                    content_type,
                    redirect_location,
                    error
                FROM monitoring_history
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

            return [
                CheckResult(
                    **{
                        **dict(row),
                        "is_healthy": bool(row["is_healthy"]),
                    }
                )
                for row in rows
            ]
        finally:
            connection.close()

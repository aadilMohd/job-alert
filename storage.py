"""SQLite-backed seen-jobs tracking to avoid duplicate alerts."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

_PRUNE_DAYS = 30


class SeenStore:
    def __init__(self, path: str = "jobs.db"):
        self._conn = sqlite3.connect(path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_jobs (
                job_id TEXT PRIMARY KEY,
                first_seen TIMESTAMP NOT NULL
            )
            """
        )
        self._conn.commit()

    def is_seen(self, job_id: str) -> bool:
        cur = self._conn.execute(
            "SELECT 1 FROM seen_jobs WHERE job_id = ?", (job_id,)
        )
        return cur.fetchone() is not None

    def mark_seen(self, job_id: str) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO seen_jobs (job_id, first_seen) VALUES (?, ?)",
            (job_id, datetime.now(timezone.utc).isoformat()),
        )
        self._conn.commit()

    def filter_new(self, job_ids: list[str]) -> list[str]:
        """Return only the job IDs not yet seen."""
        return [jid for jid in job_ids if not self.is_seen(jid)]

    def prune(self, days: int = _PRUNE_DAYS) -> int:
        """Remove entries older than `days`. Returns rows removed."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        cur = self._conn.execute(
            "DELETE FROM seen_jobs WHERE first_seen < ?", (cutoff,)
        )
        self._conn.commit()
        return cur.rowcount

    def close(self) -> None:
        self._conn.close()

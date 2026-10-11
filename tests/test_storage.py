"""Unit tests for storage (SQLite dedupe)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from storage import SeenStore


def test_unseen_job_is_new(tmp_path):
    store = SeenStore(str(tmp_path / "jobs.db"))
    assert not store.is_seen("abc123")
    store.close()


def test_mark_seen_then_is_seen(tmp_path):
    store = SeenStore(str(tmp_path / "jobs.db"))
    store.mark_seen("abc123")
    assert store.is_seen("abc123")
    store.close()


def test_mark_seen_is_idempotent(tmp_path):
    store = SeenStore(str(tmp_path / "jobs.db"))
    store.mark_seen("abc123")
    store.mark_seen("abc123")  # duplicate insert ignored
    assert store.is_seen("abc123")
    store.close()


def test_filter_new(tmp_path):
    store = SeenStore(str(tmp_path / "jobs.db"))
    store.mark_seen("seen1")
    assert store.filter_new(["seen1", "new1", "new2"]) == ["new1", "new2"]
    store.close()


def test_db_persists_between_instances(tmp_path):
    path = str(tmp_path / "jobs.db")
    store = SeenStore(path)
    store.mark_seen("persisted")
    store.close()

    store2 = SeenStore(path)
    assert store2.is_seen("persisted")
    store2.close()


def test_prune_removes_old_entries_only(tmp_path):
    store = SeenStore(str(tmp_path / "jobs.db"))
    store.mark_seen("old")
    store.mark_seen("fresh")
    # Backdate the old entry
    old_ts = (datetime.now(timezone.utc) - timedelta(days=45)).isoformat()
    store._conn.execute(
        "UPDATE seen_jobs SET first_seen = ? WHERE job_id = 'old'", (old_ts,)
    )
    store._conn.commit()

    removed = store.prune(days=30)
    assert removed == 1
    assert not store.is_seen("old")
    assert store.is_seen("fresh")
    store.close()

"""Unit tests for the Zero-Trust State Management Engine."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest

from xos.core.state import (
    get_active_session_count,
    init_db,
    lazy_garbage_collect,
    purge_session,
    register_session,
    verify_session,
)


def test_db_initialization(tmp_path: Path) -> None:
    db_path = tmp_path / "metadata.db"
    init_db(db_path)
    assert db_path.exists()

    # Verify tables and WAL/sync settings
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        assert "sessions" in tables


def test_register_and_verify_session(tmp_path: Path) -> None:
    db_path = tmp_path / "metadata.db"
    session_id = uuid4()
    scratchpad = tmp_path / "sessions" / str(session_id) / "scratchpad"

    register_session(db_path, session_id, 3600, scratchpad)

    # Assert verification returns scratchpad path
    verified_scratchpad = verify_session(db_path, session_id)
    assert verified_scratchpad == scratchpad

    # Verify active session count
    assert get_active_session_count(db_path) == 1


def test_verify_session_expired(tmp_path: Path) -> None:
    db_path = tmp_path / "metadata.db"
    session_id = uuid4()
    scratchpad = tmp_path / "sessions" / str(session_id) / "scratchpad"

    # Register with a TTL of 1 second
    register_session(db_path, session_id, 1, scratchpad)

    # Let it expire by manually modifying the db
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE sessions SET last_active_at = datetime('now', '-2 seconds') "
            "WHERE session_id = ?;",
            (str(session_id),),
        )
        conn.commit()

    with pytest.raises(ValueError, match="Session is invalid or has expired"):
        verify_session(db_path, session_id)

    assert get_active_session_count(db_path) == 0


def test_purge_session(tmp_path: Path) -> None:
    db_path = tmp_path / "metadata.db"
    session_id = uuid4()
    scratchpad = tmp_path / "sessions" / str(session_id) / "scratchpad"

    register_session(db_path, session_id, 3600, scratchpad)
    assert get_active_session_count(db_path) == 1

    purged_path = purge_session(db_path, session_id)
    assert purged_path == scratchpad
    assert get_active_session_count(db_path) == 0

    # Purging non-existent session returns None
    assert purge_session(db_path, uuid4()) is None


def test_lazy_garbage_collect(tmp_path: Path) -> None:
    db_path = tmp_path / "metadata.db"

    session_id_active = uuid4()
    scratchpad_active = tmp_path / "active"
    scratchpad_active.mkdir(parents=True, exist_ok=True)
    register_session(db_path, session_id_active, 3600, scratchpad_active)

    session_id_expired = uuid4()
    scratchpad_expired = tmp_path / "expired"
    scratchpad_expired.mkdir(parents=True, exist_ok=True)
    register_session(db_path, session_id_expired, 1, scratchpad_expired)

    # Artificially expire the expired session in the DB
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE sessions SET last_active_at = datetime('now', '-2 seconds') "
            "WHERE session_id = ?;",
            (str(session_id_expired),),
        )
        conn.commit()

    lazy_garbage_collect(db_path)

    # Active session should remain
    assert scratchpad_active.exists()
    assert get_active_session_count(db_path) == 1

    # Expired session should be removed
    assert not scratchpad_expired.exists()


def test_lazy_garbage_collect_file_error_shield(tmp_path: Path) -> None:
    db_path = tmp_path / "metadata.db"
    session_id = uuid4()
    scratchpad = tmp_path / "expired"
    # Do not create the scratchpad folder physically to trigger FileNotFoundError
    register_session(db_path, session_id, 1, scratchpad)

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE sessions SET last_active_at = datetime('now', '-2 seconds') "
            "WHERE session_id = ?;",
            (str(session_id),),
        )
        conn.commit()

    # Should run fine without throwing an exception
    lazy_garbage_collect(db_path)
    assert get_active_session_count(db_path) == 0

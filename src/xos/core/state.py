"""Zero-Trust Session and State Management Engine."""

from __future__ import annotations

import contextlib
import os
import shutil
import sqlite3
from pathlib import Path
from uuid import UUID


def get_app_data_dir() -> Path:
    """Resolve the secure root App Data Directory for XoS."""
    env_path = os.environ.get("XOS_APP_DATA_DIR")
    if env_path:
        return Path(env_path)
    return Path.home() / ".gemini" / "antigravity"


def get_db_path() -> Path:
    """Resolve the session metadata database path."""
    db_dir = get_app_data_dir() / "sessions"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "metadata.db"


def init_db(db_path: Path) -> None:
    """Initialize the session tracking schema and WAL configs."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path, timeout=30.0) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at TEXT DEFAULT (datetime('now')),
                last_active_at TEXT DEFAULT (datetime('now')),
                scratchpad_path TEXT NOT NULL,
                ttl_seconds INTEGER NOT NULL
            );
            """
        )
        conn.commit()


def register_session(
    db_path: Path,
    session_id: UUID,
    ttl_seconds: int,
    scratchpad_path: Path,
) -> None:
    """Register a new active session inside the SQLite state database."""
    init_db(db_path)
    with sqlite3.connect(db_path, timeout=30.0) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute(
            """
            INSERT INTO sessions (session_id, scratchpad_path, ttl_seconds)
            VALUES (?, ?, ?);
            """,
            (str(session_id), str(scratchpad_path), ttl_seconds),
        )
        conn.commit()


def get_active_session_count(db_path: Path) -> int:
    """Count the total number of non-expired active sessions."""
    if not db_path.exists():
        return 0
    with sqlite3.connect(db_path, timeout=30.0) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) FROM sessions
            WHERE datetime(last_active_at, '+' || ttl_seconds || ' seconds') >= datetime('now');
            """
        )
        row = cursor.fetchone()
        return int(row[0]) if row else 0


def verify_session(db_path: Path, session_id: UUID) -> Path:
    """Verify session is valid and active, and renew its lease."""
    if not db_path.exists():
        raise ValueError("Session database does not exist")
    with sqlite3.connect(db_path, timeout=30.0) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT scratchpad_path
            FROM sessions
            WHERE session_id = ?
              AND datetime(last_active_at, '+' || ttl_seconds || ' seconds') >= datetime('now');
            """,
            (str(session_id),),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError("Session is invalid or has expired")

        scratchpad_path = Path(row[0])

        # renew session lease by update last_active_at
        cursor.execute(
            "UPDATE sessions SET last_active_at = datetime('now') WHERE session_id = ?;",
            (str(session_id),),
        )
        conn.commit()
        return scratchpad_path


def purge_session(db_path: Path, session_id: UUID) -> Path | None:
    """Exclusively delete session from metadata and return its scratchpad path."""
    if not db_path.exists():
        return None
    with sqlite3.connect(db_path, timeout=30.0) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        cursor = conn.cursor()

        # Get scratchpad_path before deletion
        cursor.execute(
            "SELECT scratchpad_path FROM sessions WHERE session_id = ?;",
            (str(session_id),),
        )
        row = cursor.fetchone()
        if not row:
            return None

        scratchpad_path = Path(row[0])

        # exclusive delete from metadata database
        cursor.execute("DELETE FROM sessions WHERE session_id = ?;", (str(session_id),))
        conn.commit()
        return scratchpad_path


def lazy_garbage_collect(db_path: Path) -> None:
    """Safely purge expired sessions from database and physical filesystem.

    Performs metadata deletes first in a transaction to claim deletion ownership,
    then cleans up filesystem assets suppressing OS file errors.
    """
    if not db_path.exists():
        return

    expired_scratchpads: list[Path] = []
    with sqlite3.connect(db_path, timeout=30.0) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT session_id, scratchpad_path
            FROM sessions
            WHERE datetime(last_active_at, '+' || ttl_seconds || ' seconds') < datetime('now');
            """
        )
        expired = cursor.fetchall()
        if not expired:
            return

        session_ids = [row[0] for row in expired]
        expired_scratchpads = [Path(row[1]) for row in expired]

        # transactional metadata delete to claim exclusive deletion right
        placeholders = ",".join("?" for _ in session_ids)
        cursor.execute(
            f"DELETE FROM sessions WHERE session_id IN ({placeholders});",  # nosec B608 # noqa: S608
            session_ids,
        )
        conn.commit()

    # filesystem cleanup with concurrency exception shield
    for path in expired_scratchpads:
        if path.exists():
            with contextlib.suppress(FileNotFoundError, PermissionError):
                shutil.rmtree(path)

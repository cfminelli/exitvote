"""
SQLite database connection and table setup.

We use plain sqlite3 (no ORM) to keep things simple and visible.
Each request gets its own connection via a FastAPI dependency.
"""

import os
import sqlite3
from pathlib import Path

# DB_PATH can be overridden via the DATABASE_URL env var (Railway sets this automatically
# if you attach a volume). Falls back to a local file for development.
_default = Path(__file__).parent.parent / "exitvote.db"
DB_PATH = Path(os.environ.get("DATABASE_PATH", str(_default)))


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Open a SQLite connection with row_factory so rows behave like dicts."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # safer concurrent writes
    return conn


def init_db(db_path: Path = DB_PATH) -> None:
    """Create tables if they don't exist yet. Safe to call multiple times."""
    conn = get_connection(db_path)
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS rooms (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                code                TEXT NOT NULL UNIQUE,
                event_name          TEXT NOT NULL,
                created_at          TEXT NOT NULL DEFAULT (datetime('now')),
                expires_at          TEXT NOT NULL,
                leave_threshold     INTEGER NOT NULL DEFAULT 51,
                vote_cooldown       INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS members (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id     INTEGER NOT NULL REFERENCES rooms(id),
                token       TEXT NOT NULL UNIQUE,
                joined_at   TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS votes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id   INTEGER NOT NULL UNIQUE REFERENCES members(id),
                choice      TEXT NOT NULL CHECK(choice IN ('stay', 'leave')),
                reason      TEXT,
                voted_at    TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
    conn.close()

"""
state.py — Satu-satunya lapisan yang boleh bicara langsung ke database.
Semua modul lain akses state lewat fungsi di sini, bukan query SQLite manual.
"""

import sqlite3
import hashlib
import time
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).parent.parent / "memory" / "derry.db"
DB_PATH.parent.mkdir(exist_ok=True)


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                trust_level TEXT NOT NULL,      -- 'trusted' | 'untrusted'
                content_hash TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at REAL NOT NULL,
                handled_by TEXT                 -- 'reflex_skip' | 'reflex_direct' | 'llm' | 'blocked'
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS llm_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                tokens_used INTEGER NOT NULL,
                purpose TEXT,                    -- 'triage' | 'reasoning'
                created_at REAL NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope TEXT NOT NULL,             -- misal 'chat:telegram_123'
                summary_text TEXT NOT NULL,
                created_at REAL NOT NULL
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_events_hash ON events(content_hash, created_at)")


def make_hash(source: str, payload: str) -> str:
    return hashlib.sha256(f"{source}:{payload}".encode()).hexdigest()


def is_duplicate(content_hash: str, window_seconds: int) -> bool:
    """Cek apakah event dengan hash sama pernah masuk dalam window waktu tertentu."""
    cutoff = time.time() - window_seconds
    with _conn() as c:
        row = c.execute(
            "SELECT 1 FROM events WHERE content_hash = ? AND created_at > ? LIMIT 1",
            (content_hash, cutoff),
        ).fetchone()
    return row is not None


def log_event(source: str, trust_level: str, payload: str, handled_by: str) -> int:
    content_hash = make_hash(source, payload)
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO events (source, trust_level, content_hash, payload, created_at, handled_by) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (source, trust_level, content_hash, payload, time.time(), handled_by),
        )
        return cur.lastrowid


def log_llm_call(provider: str, tokens_used: int, purpose: str):
    with _conn() as c:
        c.execute(
            "INSERT INTO llm_calls (provider, tokens_used, purpose, created_at) VALUES (?, ?, ?, ?)",
            (provider, tokens_used, purpose, time.time()),
        )


def tokens_used_today(provider: str) -> int:
    start_of_day = time.time() - (time.time() % 86400)
    with _conn() as c:
        row = c.execute(
            "SELECT COALESCE(SUM(tokens_used), 0) as total FROM llm_calls "
            "WHERE provider = ? AND created_at > ?",
            (provider, start_of_day),
        ).fetchone()
    return row["total"]


def llm_calls_last_minute() -> int:
    cutoff = time.time() - 60
    with _conn() as c:
        row = c.execute(
            "SELECT COUNT(*) as cnt FROM llm_calls WHERE created_at > ?", (cutoff,)
        ).fetchone()
    return row["cnt"]


init_db()

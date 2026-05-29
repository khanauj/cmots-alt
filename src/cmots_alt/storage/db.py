"""SQLite handle + migrations. One file: storage/cmots_alt.sqlite."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from ..core.settings import Settings

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def _db_path(settings: Settings) -> Path:
    p = settings.resolve(settings.paths.db)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def run_migrations(settings: Settings) -> None:
    db_path = _db_path(settings)
    conn = _connect(db_path)
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS _migrations (name TEXT PRIMARY KEY, applied_at TEXT)"
        )
        applied = {r["name"] for r in conn.execute("SELECT name FROM _migrations")}
        for sql_file in sorted(_MIGRATIONS_DIR.glob("*.sql")):
            if sql_file.name in applied:
                continue
            conn.executescript(sql_file.read_text(encoding="utf-8"))
            conn.execute(
                "INSERT INTO _migrations(name, applied_at) VALUES (?, datetime('now'))",
                (sql_file.name,),
            )
        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_db(settings: Settings) -> Iterator[sqlite3.Connection]:
    conn = _connect(_db_path(settings))
    try:
        yield conn
    finally:
        conn.close()


def mint_co_code(settings: Settings) -> int:
    """Atomic increment of co_code_sequence; returns the newly assigned code."""
    with get_db(settings) as conn:
        cur = conn.execute("SELECT next_value FROM co_code_sequence")
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("co_code_sequence not initialised")
        value = int(row["next_value"])
        conn.execute("UPDATE co_code_sequence SET next_value = next_value + 1")
        conn.commit()
        return value

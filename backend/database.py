import sqlite3
import os
import time
from config import Config


def _resolve_db_path() -> str:
    path = os.path.normpath(Config.DB_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def get_connection() -> sqlite3.Connection:
    """Return a WAL-mode SQLite connection with Row factory and busy-timeout retry."""
    conn = sqlite3.connect(_resolve_db_path(), timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Apply schema.sql on startup (idempotent — uses CREATE IF NOT EXISTS)."""
    schema_path = os.path.join(os.path.dirname(__file__), 'models', 'schema.sql')
    with open(schema_path, 'r') as f:
        schema = f.read()
    with get_connection() as conn:
        conn.executescript(schema)


def get_db_status() -> bool:
    """Health-check: returns True if DB is reachable."""
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False

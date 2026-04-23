"""
Phase 4: Audit logging for provisioning.
SQLite schema and helpers for success/failure records.
"""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# Default DB next to this file
DEFAULT_DB = Path(__file__).resolve().parent / "provisioning_audit.db"


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    db_path = db_path or DEFAULT_DB
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection | None = None) -> None:
    conn = conn or get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS provisioning_success (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vin TEXT NOT NULL,
                timestamp_utc TEXT NOT NULL,
                certificate_serial INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS provisioning_failure (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp_utc TEXT NOT NULL,
                reason TEXT NOT NULL,
                client_identity TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()


def log_success(vin: str, certificate_serial: int, db_path: Path | None = None) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO provisioning_success (vin, timestamp_utc, certificate_serial) VALUES (?, ?, ?)",
            (vin, datetime.now(timezone.utc).isoformat(), certificate_serial),
        )
        conn.commit()
    finally:
        conn.close()


def log_failure(reason: str, client_identity: str | None = None, db_path: Path | None = None) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO provisioning_failure (timestamp_utc, reason, client_identity) VALUES (?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), reason, client_identity),
        )
        conn.commit()
    finally:
        conn.close()

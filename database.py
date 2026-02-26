# database.py — Zak's Deo Download
# © 2024 Zak. Tous droits réservés.

import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zaks.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_conn()
    try:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id         TEXT    PRIMARY KEY,
            session_id TEXT,
            url        TEXT    NOT NULL,
            format     TEXT    NOT NULL DEFAULT 'video_480',
            status     TEXT    NOT NULL DEFAULT 'pending',
            filename   TEXT,
            filepath   TEXT,
            error_msg  TEXT,
            created    TEXT    NOT NULL DEFAULT (datetime('now')),
            updated    TEXT    NOT NULL DEFAULT (datetime('now'))
        );
        """)
        conn.commit()
        print(f"[DB] Initialisée : {DB_PATH} ✓")
    finally:
        conn.close()

"""SQLite persistence layer. Mirrors the schema in the SRS (section 12)."""
import sqlite3
import datetime
from contextlib import contextmanager

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    last_activity TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analysis_history (
    analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    source_type TEXT,           -- 'live_capture' | 'image' | 'video' | 'docx' | 'text'
    language TEXT,
    error_type TEXT,
    question TEXT,
    ocr_text TEXT,
    analysis TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE TABLE IF NOT EXISTS code_suggestions (
    suggestion_id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER NOT NULL,
    original_code TEXT,
    suggested_code TEXT,
    test_status TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (analysis_id) REFERENCES analysis_history(analysis_id)
);

CREATE TABLE IF NOT EXISTS chat_messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    role TEXT NOT NULL,          -- 'user' | 'assistant'
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def create_session() -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO sessions (created_at, last_activity) VALUES (?, ?)",
            (_now(), _now()),
        )
        return cur.lastrowid


def touch_session(session_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE sessions SET last_activity = ? WHERE session_id = ?",
            (_now(), session_id),
        )


def save_analysis(session_id, source_type, language, error_type, question,
                   ocr_text, analysis) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO analysis_history
               (session_id, source_type, language, error_type, question,
                ocr_text, analysis, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, source_type, language, error_type, question,
             ocr_text, analysis, _now()),
        )
        return cur.lastrowid


def save_code_suggestion(analysis_id, original_code, suggested_code, test_status):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO code_suggestions
               (analysis_id, original_code, suggested_code, test_status, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (analysis_id, original_code, suggested_code, test_status, _now()),
        )


def save_chat_message(session_id, role, content):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO chat_messages (session_id, role, content, created_at) "
            "VALUES (?, ?, ?, ?)",
            (session_id, role, content, _now()),
        )


def get_chat_history(session_id, limit=30):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content FROM chat_messages WHERE session_id = ? "
            "ORDER BY message_id ASC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def get_history(limit=50):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM analysis_history ORDER BY analysis_id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def delete_analysis(analysis_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM code_suggestions WHERE analysis_id = ?", (analysis_id,))
        conn.execute("DELETE FROM analysis_history WHERE analysis_id = ?", (analysis_id,))

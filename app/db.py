import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from . import turso

DB_PATH = Path(os.environ.get("CTF_DB", Path(__file__).resolve().parent.parent / "data" / "ctf.db"))
# Si están definidas, la base de datos vive en Turso (SQLite en la nube) en vez de en un archivo local.
TURSO_URL = os.environ.get("TURSO_DATABASE_URL")
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL COLLATE NOCASE,
    pw_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS progress (
    user_id INTEGER NOT NULL REFERENCES users(id),
    challenge_id TEXT NOT NULL,
    max_hint INTEGER NOT NULL DEFAULT 0,
    solved_at TEXT,
    earned INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, challenge_id)
);
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    challenge_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_chat ON chat_messages(user_id, challenge_id, id);
CREATE TABLE IF NOT EXISTS room_answers (
    user_id INTEGER NOT NULL REFERENCES users(id),
    room_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    answer TEXT NOT NULL,
    earned INTEGER NOT NULL,
    answered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, room_id, question_id)
);
CREATE TABLE IF NOT EXISTS generated_challenges (
    id TEXT PRIMARY KEY,
    author_id INTEGER NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    points INTEGER NOT NULL,
    description TEXT NOT NULL,
    data TEXT NOT NULL,
    tutor_notes TEXT NOT NULL,
    flag_sha256 TEXT NOT NULL,
    hints TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def init_db():
    if not TURSO_URL:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(SCHEMA)
        # Migración de bases de datos creadas antes de que existieran las pistas.
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(generated_challenges)")}
        if "hints" not in cols:
            conn.execute("ALTER TABLE generated_challenges ADD COLUMN hints TEXT NOT NULL DEFAULT '[]'")


@contextmanager
def connect():
    if TURSO_URL:
        conn = turso.Connection(TURSO_URL, TURSO_TOKEN)
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

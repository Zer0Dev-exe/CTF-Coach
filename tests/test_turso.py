"""El adaptador de Turso se comporta como sqlite3 (contra un servidor Hrana falso)."""

import sqlite3
import threading

import pytest

from app import db, turso
from fake_turso import make_server


@pytest.fixture
def remote(tmp_path, monkeypatch):
    server = make_server(0, str(tmp_path / "remote.db"))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(db, "TURSO_URL", f"http://127.0.0.1:{server.server_address[1]}")
    monkeypatch.setattr(db, "TURSO_TOKEN", "test-token")
    db.init_db()
    yield tmp_path / "remote.db"
    server.shutdown()


def test_rows_cursors_and_params(remote):
    with db.connect() as conn:
        cur = conn.execute("INSERT INTO users (username, pw_hash) VALUES (?, ?)", ("ana", "x"))
        assert cur.lastrowid == 1 and cur.rowcount == 1
        conn.executemany("INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
                         [("t1", 1, "2099"), ("t2", 1, "2099")])
        row = conn.execute("SELECT id, username FROM users WHERE id = :u", {"u": 1}).fetchone()
        assert row[0] == 1 and row["username"] == "ana" and dict(row) == {"id": 1, "username": "ana"}
        assert [r["token"] for r in conn.execute("SELECT token FROM sessions ORDER BY token")] == ["t1", "t2"]
        assert conn.execute("INSERT OR IGNORE INTO users (id, username, pw_hash) VALUES (1, 'ana', 'x')").rowcount == 0


def test_unique_violation_is_integrity_error(remote):
    with db.connect() as conn:
        conn.execute("INSERT INTO users (username, pw_hash) VALUES ('ana', 'x')")
    with pytest.raises(sqlite3.IntegrityError):
        with db.connect() as conn:
            conn.execute("INSERT INTO users (username, pw_hash) VALUES ('ANA', 'y')")


def test_failed_block_rolls_back(remote):
    with pytest.raises(RuntimeError):
        with db.connect() as conn:
            conn.execute("INSERT INTO users (username, pw_hash) VALUES ('ana', 'x')")
            raise RuntimeError
    assert sqlite3.connect(remote).execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0


def test_libsql_url_becomes_https():
    assert turso.Connection("libsql://db-org.turso.io", "t")._url == "https://db-org.turso.io"


def test_pasted_credentials_are_cleaned():
    conn = turso.Connection(' "libsql://db-org.turso.io" ', "Bearer eyJabc
")
    assert conn._url == "https://db-org.turso.io" and conn._token == "eyJabc"

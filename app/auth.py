import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Cookie, HTTPException, Response

from .db import connect

SESSION_COOKIE = "ctf_session"
SESSION_DAYS = 7
SCRYPT = dict(n=2**14, r=8, p=1)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **SCRYPT)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    salt_hex, digest_hex = stored.split("$")
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), **SCRYPT)
    return hmac.compare_digest(digest.hex(), digest_hex)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def start_session(response: Response, user_id: int):
    token = secrets.token_urlsafe(32)
    expires = _now() + timedelta(days=SESSION_DAYS)
    with connect() as conn:
        conn.execute("INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
                      (token, user_id, expires.isoformat()))
    response.set_cookie(SESSION_COOKIE, token, max_age=SESSION_DAYS * 86400,
                        httponly=True, samesite="lax")


def end_session(response: Response, token: str | None):
    if token:
        with connect() as conn:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    response.delete_cookie(SESSION_COOKIE)


def optional_user(ctf_session: str | None = Cookie(default=None)) -> dict | None:
    if not ctf_session:
        return None
    with connect() as conn:
        row = conn.execute(
            "SELECT u.id, u.username, s.expires_at FROM sessions s JOIN users u ON u.id = s.user_id "
            "WHERE s.token = ?", (ctf_session,)).fetchone()
        if not row:
            return None
        if datetime.fromisoformat(row["expires_at"]) < _now():
            conn.execute("DELETE FROM sessions WHERE token = ?", (ctf_session,))
            return None
    return {"id": row["id"], "username": row["username"]}


def require_user(ctf_session: str | None = Cookie(default=None)) -> dict:
    user = optional_user(ctf_session)
    if not user:
        raise HTTPException(401, "Inicia sesión para continuar.")
    return user

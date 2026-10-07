import json
from pathlib import Path

from fastapi import HTTPException

from .db import connect

STATIC = json.loads((Path(__file__).resolve().parent / "challenges.json").read_text(encoding="utf-8"))
STATIC_BY_ID = {c["id"]: c for c in STATIC}
PUBLIC_FIELDS = ("id", "title", "category", "difficulty", "points", "description", "data")


def all_challenges() -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT g.*, u.username AS author FROM generated_challenges g "
            "JOIN users u ON u.id = g.author_id ORDER BY g.created_at").fetchall()
    return [dict(c, author=None, generated=False) for c in STATIC] + [_row(r) | {"generated": True} for r in rows]


def _row(row) -> dict:
    d = dict(row)
    d["hints"] = json.loads(d.get("hints") or "[]")
    return d


def get_challenge(cid: str) -> dict:
    if cid in STATIC_BY_ID:
        return STATIC_BY_ID[cid]
    with connect() as conn:
        row = conn.execute("SELECT * FROM generated_challenges WHERE id = ?", (cid,)).fetchone()
    if not row:
        raise HTTPException(404, "Reto no encontrado")
    return _row(row)


def public(ch: dict) -> dict:
    return {k: ch[k] for k in PUBLIC_FIELDS} | {"author": ch.get("author"), "generated": ch.get("generated", False)}

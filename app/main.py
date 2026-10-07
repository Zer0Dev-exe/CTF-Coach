import hashlib
import hmac
import json
import logging
import sqlite3
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from fastapi import Cookie, Depends, FastAPI, HTTPException, Response
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ml import analyzer

from . import assistant, auth
from . import roadmap
from . import rooms as rooms_mod
from .answers import answer_hash
from .challenges import all_challenges, get_challenge, public
from .db import connect, init_db
from .generator import Difficulty, GenerationError, generate
from . import coach

ROOT = Path(__file__).resolve().parent.parent
HINT_PENALTY = {0: 0.0, 1: 0.10, 2: 0.25, 3: 0.50}
TUTOR_MESSAGES_PER_HOUR = 200  # todo es local: el límite solo frena el abuso
GENERATIONS_PER_DAY = 20

log = logging.getLogger("ctf_coach")


@asynccontextmanager
async def lifespan(_app):
    init_db()
    analyzer.warmup()
    yield


app = FastAPI(title="CTF Coach", lifespan=lifespan)


INTERNAL_ERROR = "El Coach ha tenido un problema interno. Inténtalo de nuevo."


# ---------- Cuentas ----------

class Credentials(BaseModel):
    username: str = Field(pattern=r"^[A-Za-z0-9_]{3,20}$")
    password: str = Field(min_length=8, max_length=128)


@app.post("/api/register")
def register(body: Credentials, response: Response):
    try:
        with connect() as conn:
            cur = conn.execute("INSERT INTO users (username, pw_hash) VALUES (?, ?)",
                               (body.username, auth.hash_password(body.password)))
            user_id = cur.lastrowid
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Ese nombre de usuario ya existe.")
    auth.start_session(response, user_id)
    return {"username": body.username}


@app.post("/api/login")
def login(body: Credentials, response: Response):
    with connect() as conn:
        row = conn.execute("SELECT id, username, pw_hash FROM users WHERE username = ?", (body.username,)).fetchone()
    if not row or not auth.verify_password(body.password, row["pw_hash"]):
        raise HTTPException(401, "Usuario o contraseña incorrectos.")
    auth.start_session(response, row["id"])
    return {"username": row["username"]}


@app.post("/api/logout")
def logout(response: Response, ctf_session: str | None = Cookie(default=None)):
    auth.end_session(response, ctf_session)
    return {"ok": True}


@app.get("/api/me")
def me(user: dict | None = Depends(auth.optional_user)):
    if not user:
        return {"user": None}
    with connect() as conn:
        score = conn.execute(
            "SELECT (SELECT COALESCE(SUM(earned), 0) FROM progress WHERE user_id = :u) + "
            "(SELECT COALESCE(SUM(earned), 0) FROM room_answers WHERE user_id = :u)", {"u": user["id"]}).fetchone()[0]
    board = leaderboard("all", user)
    return {"user": user["username"], "score": score, "rank": board["me"] and board["me"]["rank"],
            "players": board["players"]}


LEADERBOARD_SIZE = 50


@app.get("/api/leaderboard")
def leaderboard(period: Literal["all", "week"] = "all", user: dict | None = Depends(auth.optional_user)):
    """Clasificación por puntos (salas + retos). Con period=week solo cuentan los puntos de los últimos 7 días."""
    since = "" if period == "all" else \
        (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    with connect() as conn:
        rows = conn.execute("""
            WITH pts AS (
                SELECT user_id, earned, solved_at AS at, 1 AS is_challenge FROM progress
                WHERE solved_at IS NOT NULL AND solved_at >= :since
                UNION ALL
                SELECT user_id, earned, answered_at, 0 FROM room_answers WHERE answered_at >= :since)
            SELECT u.id, u.username, SUM(pts.earned) AS score, SUM(pts.is_challenge) AS solved, MAX(pts.at) AS last
            FROM pts JOIN users u ON u.id = pts.user_id
            GROUP BY u.id ORDER BY score DESC, last ASC""", {"since": since}).fetchall()
        answered = conn.execute(
            "SELECT user_id, room_id, COUNT(*) AS n FROM room_answers GROUP BY user_id, room_id").fetchall()
    rooms_done: dict[int, int] = {}
    for a in answered:
        if a["n"] == rooms_mod.QUESTION_COUNT.get(a["room_id"]):
            rooms_done[a["user_id"]] = rooms_done.get(a["user_id"], 0) + 1
    ranked = [{"rank": i, "username": r["username"], "score": r["score"], "solved": r["solved"],
               "rooms": rooms_done.get(r["id"], 0), "_id": r["id"]} for i, r in enumerate(rows, 1)]

    me = None
    if user:
        mine = next((r for r in ranked if r["_id"] == user["id"]), None)
        if mine:
            ahead = ranked[mine["rank"] - 2] if mine["rank"] > 1 else None
            me = {k: v for k, v in mine.items() if k != "_id"} | {
                "gap": ahead["score"] - mine["score"] + 1 if ahead else 0,
                "ahead": ahead["username"] if ahead else None,
            }
    return {"period": period, "players": len(ranked), "me": me,
            "rows": [{k: v for k, v in r.items() if k != "_id"} for r in ranked[:LEADERBOARD_SIZE]]}


# ---------- Retos ----------

@app.get("/api/challenges")
def list_challenges(user: dict | None = Depends(auth.optional_user)):
    mine = {}
    if user:
        with connect() as conn:
            mine = {r["challenge_id"]: dict(r) for r in conn.execute(
                "SELECT challenge_id, max_hint, solved_at, earned FROM progress WHERE user_id = ?", (user["id"],))}
    out = []
    for ch in all_challenges():
        p = mine.get(ch["id"], {})
        out.append(public(ch) | {"solved": bool(p.get("solved_at")), "earned": p.get("earned", 0),
                                 "max_hint": p.get("max_hint", 0)})
    return out


class FlagSubmission(BaseModel):
    flag: str = Field(max_length=200)


@app.post("/api/challenges/{cid}/submit")
def submit_flag(cid: str, body: FlagSubmission, user: dict = Depends(auth.require_user)):
    ch = get_challenge(cid)
    digest = hashlib.sha256(body.flag.strip().encode()).hexdigest()
    if not hmac.compare_digest(digest, ch["flag_sha256"]):
        return {"correct": False}
    with connect() as conn:
        conn.execute("INSERT OR IGNORE INTO progress (user_id, challenge_id) VALUES (?, ?)", (user["id"], cid))
        p = conn.execute("SELECT max_hint, solved_at, earned FROM progress WHERE user_id = ? AND challenge_id = ?",
                         (user["id"], cid)).fetchone()
        if p["solved_at"]:
            return {"correct": True, "earned": p["earned"], "already": True}
        earned = round(ch["points"] * (1 - HINT_PENALTY[p["max_hint"]]))
        conn.execute("UPDATE progress SET solved_at = CURRENT_TIMESTAMP, earned = ? WHERE user_id = ? AND challenge_id = ?",
                     (earned, user["id"], cid))
    return {"correct": True, "earned": earned, "already": False}


# ---------- Tutor ----------

def _check_tutor_quota(user_id: int):
    with connect() as conn:
        recent = conn.execute(
            "SELECT COUNT(*) FROM chat_messages WHERE user_id = ? AND role = 'user' "
            "AND created_at > datetime('now', '-1 hour')", (user_id,)).fetchone()[0]
    if recent >= TUTOR_MESSAGES_PER_HOUR:
        raise HTTPException(429, "Has alcanzado el límite de mensajes por hora. Descansa un poco.")


def _tutor_response(user_id: int, chat_key: str, reply_fn, user_text: str, on_done=None) -> StreamingResponse:
    """Calcula la respuesta del Coach (local), la guarda y la envía en NDJSON (mismo formato que antes)."""
    def events():
        try:
            reply = reply_fn()
            with connect() as conn:
                conn.executemany(
                    "INSERT INTO chat_messages (user_id, challenge_id, role, content) VALUES (?, ?, ?, ?)",
                    [(user_id, chat_key, "user", user_text), (user_id, chat_key, "assistant", reply)])
                if on_done:
                    on_done(conn)
            yield json.dumps({"type": "done", "reply": reply}) + "\n"
        except Exception:  # la cabecera 200 ya se envió: el error viaja como evento
            log.exception("Error en el Coach")
            yield json.dumps({"type": "error", "message": INTERNAL_ERROR}) + "\n"

    return StreamingResponse(events(), media_type="application/x-ndjson")


def _history(user_id: int, cid: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT role, content FROM chat_messages WHERE user_id = ? AND challenge_id = ? ORDER BY id",
                            (user_id, cid)).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/challenges/{cid}/chat")
def get_chat(cid: str, user: dict = Depends(auth.require_user)):
    get_challenge(cid)
    return _history(user["id"], cid)


class TutorRequest(BaseModel):
    message: str = Field(default="", max_length=2000)
    level: Literal["principiante", "intermedio", "avanzado"] = "principiante"
    hint_level: Literal[1, 2, 3] | None = None


@app.post("/api/challenges/{cid}/tutor")
def tutor(cid: str, body: TutorRequest, user: dict = Depends(auth.require_user)):
    ch = get_challenge(cid)
    _check_tutor_quota(user["id"])

    def record_hint(conn):
        if body.hint_level:
            conn.execute("INSERT OR IGNORE INTO progress (user_id, challenge_id) VALUES (?, ?)", (user["id"], cid))
            conn.execute("UPDATE progress SET max_hint = MAX(max_hint, ?) "
                         "WHERE user_id = ? AND challenge_id = ? AND solved_at IS NULL",
                         (body.hint_level, user["id"], cid))

    user_text = coach.format_user_message(body.message, body.level, body.hint_level)
    return _tutor_response(user["id"], cid, lambda: coach.challenge_reply(ch, body.message, body.level, body.hint_level),
                           user_text, record_hint)


# ---------- Salas ----------

def _room_answers(user_id: int | None, room_id: str | None = None) -> dict[str, dict[str, dict]]:
    """{room_id: {question_id: {"answer", "earned"}}} del usuario."""
    if not user_id:
        return {}
    sql = "SELECT room_id, question_id, answer, earned FROM room_answers WHERE user_id = ?"
    args: tuple = (user_id,)
    if room_id:
        sql += " AND room_id = ?"
        args += (room_id,)
    out: dict[str, dict[str, dict]] = {}
    with connect() as conn:
        for r in conn.execute(sql, args):
            out.setdefault(r["room_id"], {})[r["question_id"]] = {"answer": r["answer"], "earned": r["earned"]}
    return out


def _completed_rooms(answers: dict[str, dict]) -> set[str]:
    return {rid for rid, a in answers.items() if len(a) == rooms_mod.QUESTION_COUNT.get(rid)}


@app.get("/api/rooms")
def list_rooms(user: dict | None = Depends(auth.optional_user)):
    answers = _room_answers(user and user["id"])
    paths = []
    for p in rooms_mod.PATHS:
        rooms = [rooms_mod.room_summary(r, answers.get(r["id"], {})) for r in p["rooms"]]
        paths.append({k: p[k] for k in ("id", "title", "icon", "description")} | {
            "rooms": rooms,
            "questions": sum(r["questions"] for r in rooms),
            "answered": sum(r["answered"] for r in rooms),
        })
    return {"paths": paths, "badges": rooms_mod.badges(_completed_rooms(answers))}


@app.get("/api/rooms/{rid}")
def room_detail(rid: str, user: dict | None = Depends(auth.optional_user)):
    room = rooms_mod.get_room(rid)
    return rooms_mod.public_room(room, _room_answers(user and user["id"], rid).get(rid, {}))


class AnswerSubmission(BaseModel):
    answer: str = Field(min_length=1, max_length=200)


@app.post("/api/rooms/{rid}/questions/{qid}")
def answer_question(rid: str, qid: str, body: AnswerSubmission, user: dict = Depends(auth.require_user)):
    room = rooms_mod.get_room(rid)
    q = rooms_mod.get_question(room, qid)
    digest = answer_hash(body.answer)
    if not any(hmac.compare_digest(digest, h) for h in q["answer_sha256"]):
        return {"correct": False}

    before = _room_answers(user["id"])
    with connect() as conn:
        cur = conn.execute("INSERT OR IGNORE INTO room_answers (user_id, room_id, question_id, answer, earned) "
                           "VALUES (?, ?, ?, ?, ?)", (user["id"], rid, qid, body.answer.strip(), q["points"]))
        already = cur.rowcount == 0
    after = _room_answers(user["id"])
    old = {b["id"] for b in rooms_mod.badges(_completed_rooms(before))}
    new_badges = [b for b in rooms_mod.badges(_completed_rooms(after)) if b["id"] not in old]
    return {"correct": True, "already": already, "earned": 0 if already else q["points"],
            "room_completed": rid in _completed_rooms(after), "new_badges": new_badges}


class RoomTutorRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    level: Literal["principiante", "intermedio", "avanzado"] = "principiante"
    task_id: str | None = Field(default=None, max_length=10)


@app.get("/api/rooms/{rid}/chat")
def room_chat(rid: str, user: dict = Depends(auth.require_user)):
    rooms_mod.get_room(rid)
    return _history(user["id"], f"room:{rid}")


@app.post("/api/rooms/{rid}/tutor")
def room_tutor(rid: str, body: RoomTutorRequest, user: dict = Depends(auth.require_user)):
    room = rooms_mod.get_room(rid)
    _check_tutor_quota(user["id"])
    task = rooms_mod.get_task(room, body.task_id) or room["tasks"][0]
    answered = set(_room_answers(user["id"], rid).get(rid, {}))
    user_text = coach.format_user_message(body.message, body.level, None, task["title"])
    return _tutor_response(user["id"], f"room:{rid}", lambda: coach.room_reply(task, body.message, body.level, answered),
                           user_text)


# ---------- Generación de retos (procedural, local) ----------

class GenerateRequest(BaseModel):
    theme: str = Field(default="", max_length=200)
    difficulty: Difficulty = "Media"


@app.post("/api/generate")
def generate_challenge(body: GenerateRequest, user: dict = Depends(auth.require_user)):
    with connect() as conn:
        today = conn.execute("SELECT COUNT(*) FROM generated_challenges WHERE author_id = ? "
                             "AND created_at > datetime('now', '-1 day')", (user["id"],)).fetchone()[0]
    if today >= GENERATIONS_PER_DAY:
        raise HTTPException(429, f"Puedes generar como máximo {GENERATIONS_PER_DAY} retos al día.")
    try:
        ch = generate(body.theme, body.difficulty)
    except GenerationError as e:
        raise HTTPException(422, str(e))
    with connect() as conn:
        conn.execute(
            "INSERT INTO generated_challenges (id, author_id, title, category, difficulty, points, description, "
            "data, tutor_notes, flag_sha256, hints) VALUES (:id, :author_id, :title, :category, :difficulty, :points, "
            ":description, :data, :tutor_notes, :flag_sha256, :hints)",
            ch | {"author_id": user["id"], "hints": json.dumps(ch["hints"], ensure_ascii=False)})
    return public(ch | {"author": user["username"], "generated": True})


# ---------- Roadmap ----------

@app.get("/api/roadmap")
def get_roadmap(user: dict | None = Depends(auth.optional_user)):
    solved: set[str] = set()
    if user:
        with connect() as conn:
            solved = {r[0] for r in conn.execute(
                "SELECT challenge_id FROM progress WHERE user_id = ? AND solved_at IS NOT NULL", (user["id"],))}
    return roadmap.build(_room_answers(user and user["id"]), solved)


# ---------- Bit, la mascota ----------

class AssistantRequest(BaseModel):
    message: str = Field(default="", max_length=500)
    view: str = Field(default="landing", max_length=20)


@app.post("/api/assistant")
def ask_assistant(body: AssistantRequest, user: dict | None = Depends(auth.optional_user)):
    solved: set[str] = set()
    rank = None
    if user:
        with connect() as conn:
            solved = {r[0] for r in conn.execute(
                "SELECT challenge_id FROM progress WHERE user_id = ? AND solved_at IS NOT NULL", (user["id"],))}
        rank = leaderboard("all", user)["me"]
    ctx = {"user": user and user["username"], "answers": _room_answers(user and user["id"]), "solved": solved, "rank": rank}
    return assistant.reply(body.message, body.view, ctx)


# ---------- Analizador local (modelo propio, sin API) ----------

class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


@app.post("/api/analyze")
def analyze_text(body: AnalyzeRequest):
    start = time.perf_counter()
    try:
        result = analyzer.analyze(body.text)
    except analyzer.ModelMissing as e:
        raise HTTPException(503, str(e))
    return result | {"elapsed_ms": round((time.perf_counter() - start) * 1000, 2)}


app.mount("/", StaticFiles(directory=ROOT / "static", html=True), name="static")

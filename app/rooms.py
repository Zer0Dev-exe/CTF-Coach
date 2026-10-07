"""Salas de aprendizaje al estilo THM: rutas → salas → tareas → preguntas."""

import json
from pathlib import Path

from fastapi import HTTPException

PATHS = json.loads((Path(__file__).resolve().parent / "rooms.json").read_text(encoding="utf-8"))
ROOMS = {r["id"]: r | {"path_id": p["id"]} for p in PATHS for r in p["rooms"]}
QUESTION_COUNT = {rid: sum(len(t["questions"]) for t in r["tasks"]) for rid, r in ROOMS.items()}


def get_room(rid: str) -> dict:
    if rid not in ROOMS:
        raise HTTPException(404, "Sala no encontrada")
    return ROOMS[rid]


def get_question(room: dict, qid: str) -> dict:
    for task in room["tasks"]:
        for q in task["questions"]:
            if q["id"] == qid:
                return q
    raise HTTPException(404, "Pregunta no encontrada")


def get_task(room: dict, tid: str | None) -> dict | None:
    return next((t for t in room["tasks"] if t["id"] == tid), None)


def room_summary(room: dict, answered: dict[str, dict]) -> dict:
    done = len(answered)
    return {k: room[k] for k in ("id", "title", "icon", "difficulty", "summary")} | {
        "questions": QUESTION_COUNT[room["id"]], "answered": done,
        "completed": done == QUESTION_COUNT[room["id"]],
    }


def public_room(room: dict, answered: dict[str, dict]) -> dict:
    """answered: {question_id: {"answer": ..., "earned": ...}} del usuario actual."""
    tasks = []
    for t in room["tasks"]:
        questions = [{k: q[k] for k in ("id", "prompt", "points", "options", "mask")}
                     | {"answered": q["id"] in answered, "answer": answered.get(q["id"], {}).get("answer")}
                     for q in t["questions"]]
        tasks.append({k: t[k] for k in ("id", "title", "content", "data")} | {"questions": questions})
    return room_summary(room, answered) | {"path_id": room["path_id"], "tasks": tasks}


def badges(completed_rooms: set[str]) -> list[dict]:
    out = [{"id": f"room:{rid}", "icon": ROOMS[rid]["icon"], "name": ROOMS[rid]["title"], "kind": "sala"}
           for rid in ROOMS if rid in completed_rooms]
    for p in PATHS:
        if all(r["id"] in completed_rooms for r in p["rooms"]):
            out.append({"id": f"path:{p['id']}", "icon": p["icon"], "name": f"Ruta {p['title']}", "kind": "ruta"})
    return out

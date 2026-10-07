"""Pruebas de la API. Todo es local: no hay servicios externos ni claves."""

import os
import random
import sys
import tempfile
from pathlib import Path

os.environ["CTF_DB"] = str(Path(tempfile.mkdtemp()) / "test.db")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import build_challenges  # noqa: E402
import build_rooms  # noqa: E402
from app import coach, generator, main, rooms  # noqa: E402
from app.challenges import STATIC_BY_ID  # noqa: E402

FLAGS = {c["id"]: c["flag"] for c in build_challenges.build()}


@pytest.fixture(scope="module")
def client():
    with TestClient(main.app) as c:
        yield c


def register(client, name, password="contraseña123"):
    c = TestClient(main.app)
    c.__enter__()
    r = c.post("/api/register", json={"username": name, "password": password})
    assert r.status_code == 200, r.text
    return c


def test_challenges_do_not_leak_secrets(client):
    chs = client.get("/api/challenges").json()
    assert len(chs) == 7
    for ch in chs:
        assert "flag_sha256" not in ch and "tutor_notes" not in ch


def test_register_login_logout(client):
    c = register(client, "ana")
    assert c.get("/api/me").json()["user"] == "ana"
    assert c.post("/api/register", json={"username": "ANA", "password": "otraclave99"}).status_code == 409
    c.post("/api/logout")
    assert c.get("/api/me").json() == {"user": None}
    assert c.post("/api/login", json={"username": "ana", "password": "incorrecta1"}).status_code == 401
    assert c.post("/api/login", json={"username": "ana", "password": "contraseña123"}).status_code == 200


def test_submit_requires_login(client):
    r = client.post("/api/challenges/capas/submit", json={"flag": FLAGS["capas"]})
    assert r.status_code == 401


def test_scoring_and_leaderboard(client):
    c = register(client, "beto")

    # Pista de nivel 2 en 'cesar' -> 25% de penalización
    r = c.post("/api/challenges/cesar/tutor", json={"hint_level": 2})
    lines = [l for l in r.text.splitlines() if l]
    assert '"done"' in lines[-1] and "Pista 2" in lines[-1]
    assert len(c.get("/api/challenges/cesar/chat").json()) == 2

    assert c.post("/api/challenges/cesar/submit", json={"flag": "flag{mal}"}).json() == {"correct": False}
    assert c.post("/api/challenges/cesar/submit", json={"flag": FLAGS["cesar"]}).json()["earned"] == 75
    assert c.post("/api/challenges/capas/submit", json={"flag": FLAGS["capas"]}).json()["earned"] == 100
    again = c.post("/api/challenges/capas/submit", json={"flag": FLAGS["capas"]}).json()
    assert again["already"] and again["earned"] == 100

    # Pedir pistas después de resolverlo no resta puntos
    c.post("/api/challenges/capas/tutor", json={"hint_level": 3})
    assert c.get("/api/me").json()["score"] == 175

    board = client.get("/api/leaderboard").json()
    assert board["rows"][0] == {"rank": 1, "username": "beto", "score": 175, "solved": 2, "rooms": 0}
    assert board["me"] is None and board["players"] >= 1
    me = c.get("/api/leaderboard?period=week").json()["me"]
    assert me["rank"] == 1 and me["gap"] == 0 and me["ahead"] is None
    assert client.get("/api/leaderboard?period=year").status_code == 422


def test_coach_error_does_not_penalize(client, monkeypatch):
    def broken(*a):
        raise RuntimeError("fallo interno")

    monkeypatch.setattr(main.coach, "challenge_reply", broken)
    c = register(client, "carla")
    r = c.post("/api/challenges/xor/tutor", json={"hint_level": 3})
    assert r.status_code == 200 and '"error"' in r.text
    ch = next(x for x in c.get("/api/challenges").json() if x["id"] == "xor")
    assert ch["max_hint"] == 0
    assert c.get("/api/challenges/xor/chat").json() == []


@pytest.mark.parametrize("difficulty", ["Fácil", "Media", "Difícil"])
def test_generated_challenges_are_solvable(difficulty):
    ops = ["base64", "base32", "hex", "rot13", "caesar", "atbash", "reverse", "xor"]
    rng = random.Random(difficulty)
    for _ in range(300):
        steps = [generator.Step(op=rng.choice(ops), param=rng.randint(0, 300)) for _ in range(rng.randint(0, 7))]
        idea = generator.ChallengeIdea(title="T", story="Historia", keyword="Pirata Ñ!", steps=steps)
        ch = generator.build(idea, difficulty)  # build() ya verifica que se puede invertir
        assert ch["data"].isprintable()
        assert ch["points"] == generator.POINTS[difficulty]


def test_generate_endpoint(client, monkeypatch):
    idea = generator.ChallengeIdea(
        title="El tesoro del capitán", story="Un mapa escrito al revés...", keyword="tesoro",
        steps=[generator.Step(op="reverse", param=0), generator.Step(op="base64", param=0)])
    monkeypatch.setattr(main, "generate", lambda theme, difficulty: generator.build(idea, difficulty))
    c = register(client, "dani")
    r = c.post("/api/generate", json={"theme": "piratas", "difficulty": "Media"})
    assert r.status_code == 200, r.text
    ch = r.json()
    assert ch["generated"] and ch["author"] == "dani" and ch["id"].startswith("gen-")
    assert any(x["id"] == ch["id"] for x in client.get("/api/challenges").json())

    for _ in range(main.GENERATIONS_PER_DAY - 1):
        assert c.post("/api/generate", json={"difficulty": "Fácil"}).status_code == 200
    assert c.post("/api/generate", json={"difficulty": "Fácil"}).status_code == 429


def test_local_analyzer(client):
    import json as _json
    data = {c["id"]: c["data"] for c in _json.loads((ROOT / "app" / "challenges.json").read_text(encoding="utf-8"))}
    expected = {"capas": "hex", "cesar": "cesar", "xor": "xor", "jwt": "jwt", "logs": "texto"}
    for cid, label in expected.items():
        r = client.post("/api/analyze", json={"text": data[cid]})
        assert r.status_code == 200, r.text
        assert r.json()["predictions"][0]["label"] == label, cid
    md5 = data["hash"].split()[1]
    assert client.post("/api/analyze", json={"text": md5}).json()["predictions"][0]["label"] == "md5"

    res = client.post("/api/analyze", json={"text": data["cesar"]}).json()
    freq = res["frequencies"]
    assert len(freq["letters"]) == len(freq["text"]) == len(freq["spanish"]) == 26
    assert abs(sum(freq["text"]) - 100) < 0.5 and res["elapsed_ms"] >= 0
    # La gráfica de letras no tiene sentido para hex, Base64 o hashes
    assert client.post("/api/analyze", json={"text": data["capas"]}).json()["frequencies"] is None
    assert client.post("/api/analyze", json={"text": ""}).status_code == 422
    assert client.post("/api/analyze", json={"text": "abc"}).json()["frequencies"] is None


def test_analyzer_real_cases_and_speed():
    """Casos escritos a mano (ml/benchmark.py): el modelo debe acertarlos y responder en pocos milisegundos."""
    import statistics
    import time
    from ml import analyzer, benchmark

    hits = sum(analyzer.predict(t)[0]["label"] == e for t, e in benchmark.CASES)
    assert hits / len(benchmark.CASES) >= 0.95, f"{hits}/{len(benchmark.CASES)}"
    times = []
    for text, _ in benchmark.CASES * 3:
        t0 = time.perf_counter()
        analyzer.analyze(text)
        times.append(time.perf_counter() - t0)
    assert statistics.median(times) < 0.01, f"mediana {statistics.median(times) * 1000:.1f} ms"


def test_fastforest_matches_sklearn():
    """La inferencia propia debe dar exactamente las mismas probabilidades que scikit-learn."""
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier
    from ml.fastforest import FastForest

    rng = np.random.default_rng(0)
    X = rng.normal(size=(400, 6)).astype(np.float32)
    y = (X[:, 0] + X[:, 1] * X[:, 2] > 0).astype(int) + (X[:, 3] > 1)
    rf = RandomForestClassifier(n_estimators=20, random_state=0).fit(X, y)
    assert np.allclose(FastForest.from_sklearn(rf).predict_proba(X), rf.predict_proba(X), atol=1e-6)


ROOM_ANSWERS = {
    room["id"]: {f"t{ti}q{qi}": q["answers"][0]
                 for ti, task in enumerate(room["tasks"], 1) for qi, q in enumerate(task["questions"], 1)}
    for path in build_rooms.PATHS for room in path["rooms"]
}


def test_rooms_do_not_leak_answers(client):
    data = client.get("/api/rooms").json()
    assert len(data["paths"]) == 4 and data["badges"] == []
    text = client.get("/api/rooms/hashes").text
    assert "answer_sha256" not in text and "tutor_notes" not in text


def test_room_answers_badges_and_score(client, monkeypatch):
    c = register(client, "fede")
    assert client.post("/api/rooms/redes/questions/t1q1", json={"answer": "22"}).status_code == 401
    assert c.post("/api/rooms/redes/questions/t1q1", json={"answer": "23"}).json() == {"correct": False}

    # Normalización: mayúsculas, tildes y espacios no importan
    r = c.post("/api/rooms/codificacion/questions/t2q1", json={"answer": "  SIMETRICO "}).json()
    assert r["correct"] and r["earned"] == 10
    assert c.post("/api/rooms/codificacion/questions/t2q1", json={"answer": "simétrico"}).json()["already"]

    # Completar la ruta Fundamentos: insignias de las dos salas y de la ruta
    badges = []
    for rid in ("redes", "linux"):
        for qid, ans in ROOM_ANSWERS[rid].items():
            r = c.post(f"/api/rooms/{rid}/questions/{qid}", json={"answer": ans}).json()
            assert r["correct"], (rid, qid)
            badges += [b["id"] for b in r["new_badges"]]
    assert badges == ["room:redes", "room:linux", "path:fundamentos"]

    room = c.get("/api/rooms/redes").json()
    assert room["completed"] and room["tasks"][0]["questions"][0]["answer"] == "22"
    fund = next(p for p in c.get("/api/rooms").json()["paths"] if p["id"] == "fundamentos")
    assert fund["answered"] == fund["questions"]

    expected = 10 + sum(q["points"] for p in build_rooms.PATHS if p["id"] == "fundamentos"
                        for room in p["rooms"] for t in room["tasks"] for q in t["questions"])
    assert c.get("/api/me").json()["score"] == expected
    board = c.get("/api/leaderboard").json()
    row = next(r for r in board["rows"] if r["username"] == "fede")
    assert board["me"]["username"] == "fede" and board["me"]["ahead"] == "beto"
    assert board["me"]["gap"] == 175 - board["me"]["score"] + 1
    assert row["rooms"] == 2 and row["solved"] == 0


def test_room_coach_points_to_theory(client):
    c = register(client, "gala")
    r = c.post("/api/rooms/redes/tutor", json={"message": "no sé qué puerto es", "task_id": "t1"})
    reply = [l for l in r.text.splitlines() if l][-1]
    assert '"done"' in reply and "SSH" in reply and "22" not in reply
    chat = c.get("/api/rooms/redes/chat").json()
    assert len(chat) == 2 and "[Tarea: Direcciones IP y puertos]" in chat[0]["content"]
    assert c.get("/api/challenges/capas/chat").json() == []


def test_every_room_answer_is_accepted():
    from app import rooms
    from app.answers import answer_hash
    for rid, answers in ROOM_ANSWERS.items():
        room = rooms.get_room(rid)
        for qid, ans in answers.items():
            assert answer_hash(ans) in rooms.get_question(room, qid)["answer_sha256"], (rid, qid)

def test_roadmap_progress(client):
    stages = client.get("/api/roadmap").json()
    assert [s["id"] for s in stages] == ["fundamentos", "bases", "blue", "red", "especializacion"]
    topics = {t["id"]: t for s in stages for t in s["topics"]}
    assert topics["redes"]["status"] == "disponible" and topics["siem"]["status"] == "externo"
    assert all(r["url"].startswith("https://") for t in topics.values() for r in t["resources"])

    c = register(client, "hugo")
    c.post("/api/rooms/redes/questions/t1q1", json={"answer": "22"})
    c.post("/api/challenges/capas/submit", json={"flag": FLAGS["capas"]})
    topics = {t["id"]: t for s in c.get("/api/roadmap").json() for t in s["topics"]}
    assert topics["redes"]["status"] == "en_curso" and topics["redes"]["done"] == 1
    assert topics["cripto"]["challenges"][0] == {"id": "capas", "title": "Capas de cebolla", "solved": True}

    for qid, ans in ROOM_ANSWERS["redes"].items():
        c.post(f"/api/rooms/redes/questions/{qid}", json={"answer": ans})
    topics = {t["id"]: t for s in c.get("/api/roadmap").json() for t in s["topics"]}
    assert topics["redes"]["status"] == "completado"

def test_internal_generator_builds_playable_challenges(client):
    """El generador es procedural: sin red, resoluble, con historia, pistas y tema en la flag."""
    for difficulty in ("Fácil", "Media", "Difícil"):
        for seed in range(40):
            ch = generator.generate("los piratas del Caribe", difficulty, random.Random(seed))
            assert len(ch["hints"]) == 3 and "piratas" in ch["description"]
            layers = ch["tutor_notes"].count("; luego ") + 1
            lo, hi = generator.STEP_RANGE[difficulty]
            assert lo <= layers <= hi + 1, (difficulty, layers, ch["tutor_notes"])  # +1: hex tras un XOR final
            assert ch["data"].isprintable() and ch["points"] == generator.POINTS[difficulty]
    ch = generator.generate("", "Media", random.Random(1))  # sin tema: elige uno
    assert ch["title"] and ch["description"]

    c = register(client, "ines")
    r = c.post("/api/generate", json={"theme": "asfasd", "difficulty": "Difícil"})
    assert r.status_code == 200, r.text
    gid = r.json()["id"]
    hint = [l for l in c.post(f"/api/challenges/{gid}/tutor", json={"hint_level": 1}).text.splitlines() if l][-1]
    assert "Pista 1" in hint


def _contains(reply: str, answer: str) -> bool:
    import re
    from app.answers import normalize
    a = normalize(answer)
    if len(a) == 1 and a.isalpha():
        return False  # "a" es una palabra normal
    return re.search(rf"(?<![\w-]){re.escape(a)}(?![\w-])", normalize(reply)) is not None


ATTEMPTS = ["", "no sé por dónde empezar", "dame la respuesta", "cuál es la solución?", "qué es esto",
            "no entiendo la pregunta", "hola", "explícame el concepto", "c2VndXJpZGFk"]


def test_room_coach_never_reveals_answers():
    for path in build_rooms.PATHS:
        for room in path["rooms"]:
            served = rooms.get_room(room["id"])
            for ti, task in enumerate(room["tasks"]):
                for q in task["questions"]:
                    for msg in ATTEMPTS + [q["prompt"]]:
                        for level in ("principiante", "avanzado"):
                            reply = coach.room_reply(served["tasks"][ti], msg, level, set())
                            for other in task["questions"]:
                                for ans in other["answers"]:
                                    assert not _contains(reply, ans), (room["id"], q["prompt"], msg, ans, reply)


def test_challenge_coach_never_reveals_flags():
    for cid, flag in FLAGS.items():
        ch = STATIC_BY_ID[cid]
        inner = flag[len("flag{"):-1]
        for msg in ATTEMPTS + [ch["data"][:200], "dame la flag"]:
            for hint in (None, 1, 2, 3):
                reply = coach.challenge_reply(ch, msg, "principiante", hint)
                assert inner not in reply and flag not in reply, (cid, msg, hint)


def test_coach_recognizes_pasted_data_and_flags():
    ch = STATIC_BY_ID["capas"]
    assert "Hexadecimal" in coach.challenge_reply(ch, ch["data"], "intermedio", None)
    assert "Enviar flag" in coach.challenge_reply(ch, "creo que es flag{algo}", "intermedio", None)
    assert "no te la voy a dar" in coach.challenge_reply(ch, "dame la flag", "intermedio", None)


BIT_CASES = [
    ("hola", None),
    ("¿por dónde empiezo?", "#sala/redes"),
    ("llévame a la sala de linux", "#sala/linux"),
    ("quiero hacer el reto del xor", "#reto/xor"),
    ("dónde está el analizador", "#reto/capas"),
    ("cómo pido pistas", "#reto/capas"),
    ("quiero crear un reto", "#retos"),
    ("dónde veo mis insignias", "#salas"),
    ("qué es XSS", "#sala/owasp"),
    ("qué es base64", "#sala/codificacion"),
    ("háblame de forense digital", "#roadmap"),
    ("llévame al roadmap", "#roadmap"),
    ("cómo funcionan los puntos", "#clasificacion"),
    ("ver la clasificación semanal", "#clasificacion"),
    ("cómo cambio el nivel del coach", "#sala/redes"),
    ("phishing", "#sala/phishing"),
    ("dónde meto la flag", "#reto/capas"),
]


def test_bit_understands_common_questions(client):
    for msg, goto in BIT_CASES:
        r = client.post("/api/assistant", json={"message": msg, "view": "landing"}).json()
        assert r["reply"], msg
        gotos = [a.get("goto") for a in r["actions"]]
        if goto:
            assert goto in gotos, (msg, gotos, r["reply"])
    r = client.post("/api/assistant", json={"message": "crear cuenta"}).json()
    assert any(a.get("auth") == "register" for a in r["actions"])
    r = client.post("/api/assistant", json={"message": "asdkjh qwe"}).json()
    assert "No estoy seguro" in r["reply"] and r["suggestions"]


def test_bit_is_personalized(client):
    c = register(client, "bit_user")
    for qid, ans in ROOM_ANSWERS["redes"].items():
        c.post(f"/api/rooms/redes/questions/{qid}", json={"answer": ans})
    nxt = c.post("/api/assistant", json={"message": "qué hago ahora"}).json()
    assert any(a.get("goto") == "#sala/linux" for a in nxt["actions"]), nxt
    prog = c.post("/api/assistant", json={"message": "mi progreso"}).json()["reply"]
    assert "Salas completadas: **1/8**" in prog and "#" in prog
    here = c.post("/api/assistant", json={"message": "qué hay en esta página", "view": "challenge"}).json()
    assert "reto" in here["reply"]


def test_bit_links_point_to_real_things(client):
    import re
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
    msgs = [m for m, _ in BIT_CASES] + ["mi progreso", "qué hay en esta página", "cerrar sesión", "filtrar el roadmap",
                                         "hablar con el coach", "copiar los datos", "cloud", "malware", "jwt"]
    seen = 0
    for view in ["landing", "roadmap", "rooms", "room", "play", "challenge", "leaderboard"]:
        for msg in msgs:
            for a in client.post("/api/assistant", json={"message": msg, "view": view}).json()["actions"]:
                goto, hl = a.get("goto"), a.get("highlight")
                if goto:
                    m = re.match(r"#(sala|reto)/(.+)", goto)
                    if m and m[1] == "sala":
                        assert m[2] in rooms.ROOMS, goto
                    elif m:
                        assert m[2] in STATIC_BY_ID, goto
                    else:
                        assert goto in ("#salas", "#retos", "#roadmap", "#clasificacion", "#inicio"), goto
                if hl:
                    seen += 1
                    name = re.match(r"[#.]([\w-]+)", hl)[1]
                    assert name in html or name in js, hl
    assert seen > 10


def test_bit_understands_its_own_suggestions(client):
    """Cada sugerencia que ofrece Bit debe tener una respuesta útil (no la de «no te he entendido»)."""
    from app import assistant
    phrases = {p for lst in assistant.VIEW_SUGGESTIONS.values() for p in lst} | set(assistant.DEFAULT_SUGGESTIONS)
    for phrase in phrases:
        for view in assistant.VIEW_SUGGESTIONS:
            r = client.post("/api/assistant", json={"message": phrase, "view": view}).json()
            assert "No estoy seguro" not in r["reply"], (phrase, view)
    r = client.post("/api/assistant", json={"message": "¿Cómo creo un reto?"}).json()
    assert any(a.get("highlight") == "#gen-form" for a in r["actions"]), r

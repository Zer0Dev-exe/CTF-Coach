"""Servidor que imita la API HTTP de Turso (Hrana 3) sobre un SQLite local.

Sirve para probar app/turso.py sin cuenta ni red:
    python tests/fake_turso.py 8099 /ruta/db.sqlite
"""

import base64
import json
import secrets
import sqlite3
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _decode(v):
    if v["type"] == "null":
        return None
    if v["type"] == "integer":
        return int(v["value"])
    if v["type"] == "float":
        return float(v["value"])
    if v["type"] == "blob":
        return base64.b64decode(v["base64"])
    return v["value"]


def _encode(v):
    if v is None:
        return {"type": "null"}
    if isinstance(v, int):
        return {"type": "integer", "value": str(v)}
    if isinstance(v, float):
        return {"type": "float", "value": v}
    if isinstance(v, bytes):
        return {"type": "blob", "base64": base64.b64encode(v).decode()}
    return {"type": "text", "value": v}


def make_server(port: int, db_path: str) -> ThreadingHTTPServer:
    streams: dict[str, sqlite3.Connection] = {}
    lock = threading.Lock()

    def execute(conn, stmt):
        if "named_args" in stmt:
            params = {a["name"][1:]: _decode(a["value"]) for a in stmt["named_args"]}
        else:
            params = [_decode(a) for a in stmt.get("args", [])]
        before = conn.total_changes
        cur = conn.execute(stmt["sql"], params)
        cols = [{"name": d[0], "decltype": None} for d in cur.description or []]
        rows = [[_encode(v) for v in r] for r in cur.fetchall()]
        return {"cols": cols, "rows": rows, "affected_row_count": conn.total_changes - before,
                "last_insert_rowid": str(cur.lastrowid) if cur.lastrowid else None}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            if self.path != "/v3/pipeline" or self.headers.get("Authorization") != "Bearer test-token":
                self.send_response(401)
                self.end_headers()
                return
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            with lock:
                baton = body["baton"]
                conn = streams.pop(baton) if baton else sqlite3.connect(db_path, isolation_level=None,
                                                                         check_same_thread=False)
                results, closed = [], False
                for req in body["requests"]:
                    try:
                        if req["type"] == "execute":
                            results.append({"type": "ok", "response": {
                                "type": "execute", "result": execute(conn, req["stmt"])}})
                        elif req["type"] == "sequence":
                            # executescript haría COMMIT por su cuenta; Turso no lo hace
                            for part in req["sql"].split(";"):
                                if part.strip():
                                    conn.execute(part)
                            results.append({"type": "ok", "response": {"type": "sequence"}})
                        elif req["type"] == "close":
                            if conn.in_transaction:
                                conn.execute("ROLLBACK")
                            conn.close()
                            closed = True
                            results.append({"type": "ok", "response": {"type": "close"}})
                    except sqlite3.Error as e:
                        code = "SQLITE_CONSTRAINT" if isinstance(e, sqlite3.IntegrityError) else "SQLITE_ERROR"
                        results.append({"type": "error", "error": {"message": str(e), "code": code}})
                new_baton = None
                if not closed:
                    new_baton = secrets.token_hex(8)
                    streams[new_baton] = conn
            data = json.dumps({"baton": new_baton, "base_url": None, "results": results}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


if __name__ == "__main__":
    make_server(int(sys.argv[1]), sys.argv[2]).serve_forever()

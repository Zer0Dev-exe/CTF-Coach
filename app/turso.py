"""Conexión mínima a Turso (libSQL) por HTTP con la misma interfaz que sqlite3.

Solo cubre lo que usa la app: execute, executemany, executescript, fetchone,
fetchall, iteración, lastrowid, rowcount y filas accesibles por índice o por
nombre. Cada `connect()` abre un stream con una transacción (BEGIN ... COMMIT),
igual que sqlite3, y no necesita dependencias: usa urllib.
"""

import base64
import json
import sqlite3
import urllib.error
import urllib.request


class Row(tuple):
    """Fila que se lee como sqlite3.Row: row[0], row["col"] y dict(row)."""

    def __new__(cls, values, names):
        row = super().__new__(cls, values)
        row._names = names
        return row

    def keys(self):
        return list(self._names)

    def __getitem__(self, key):
        if isinstance(key, str):
            return super().__getitem__(self._names.index(key))
        return super().__getitem__(key)


class Cursor:
    def __init__(self, result):
        names = [c["name"] for c in result["cols"]]
        self._rows = [Row([_decode(v) for v in r], names) for r in result["rows"]]
        self.rowcount = result["affected_row_count"]
        rowid = result.get("last_insert_rowid")
        self.lastrowid = int(rowid) if rowid is not None else None

    def fetchone(self):
        return self._rows.pop(0) if self._rows else None

    def fetchall(self):
        rows, self._rows = self._rows, []
        return rows

    def __iter__(self):
        return iter(self.fetchall())


def _encode(value):
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        value = int(value)
    if isinstance(value, int):
        return {"type": "integer", "value": str(value)}
    if isinstance(value, float):
        return {"type": "float", "value": value}
    if isinstance(value, bytes):
        return {"type": "blob", "base64": base64.b64encode(value).decode()}
    return {"type": "text", "value": str(value)}


def _decode(value):
    kind = value["type"]
    if kind == "null":
        return None
    if kind == "integer":
        return int(value["value"])
    if kind == "float":
        return float(value["value"])
    if kind == "blob":
        return base64.b64decode(value["base64"])
    return value["value"]


def _stmt(sql, params=()):
    stmt = {"sql": sql, "want_rows": True}
    if isinstance(params, dict):
        stmt["named_args"] = [{"name": k if k[0] in ":@$" else f":{k}", "value": _encode(v)}
                              for k, v in params.items()]
    else:
        stmt["args"] = [_encode(v) for v in params]
    return stmt


class Connection:
    def __init__(self, url: str, token: str):
        self._url = url.replace("libsql://", "https://", 1).rstrip("/")
        self._token = token
        self._baton = None
        self._open = False  # ¿ya se envió BEGIN?
        self.row_factory = None  # se ignora: las filas siempre son Row

    def _pipeline(self, requests):
        body = json.dumps({"baton": self._baton, "requests": requests}).encode()
        req = urllib.request.Request(f"{self._url}/v3/pipeline", data=body, method="POST", headers={
            "Authorization": f"Bearer {self._token}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.load(resp)
        except urllib.error.HTTPError as e:
            raise sqlite3.OperationalError(f"Turso HTTP {e.code}: {e.read().decode(errors='replace')}") from e
        self._baton = data.get("baton")
        if data.get("base_url"):
            self._url = data["base_url"].rstrip("/")
        results = []
        for res in data["results"]:
            if res["type"] == "error":
                err = res["error"]
                text = f"{err.get('code') or ''} {err['message']}".upper()
                exc = sqlite3.IntegrityError if "CONSTRAINT" in text else sqlite3.OperationalError
                raise exc(err["message"])
            results.append(res["response"])
        return results

    def _run(self, requests):
        if not self._open:
            # foreign_keys no tiene efecto dentro de una transacción: va antes de BEGIN
            requests = [{"type": "execute", "stmt": _stmt("PRAGMA foreign_keys = ON")},
                        {"type": "execute", "stmt": _stmt("BEGIN")}] + requests
            self._open = True
            return self._pipeline(requests)[2:]
        return self._pipeline(requests)

    def execute(self, sql, params=()):
        if sql.strip().upper().startswith("PRAGMA FOREIGN_KEYS"):
            return Cursor({"cols": [], "rows": [], "affected_row_count": 0})
        res = self._run([{"type": "execute", "stmt": _stmt(sql, params)}])
        return Cursor(res[0]["result"])

    def executemany(self, sql, seq):
        res = self._run([{"type": "execute", "stmt": _stmt(sql, p)} for p in seq])
        return Cursor({"cols": [], "rows": [],
                       "affected_row_count": sum(r["result"]["affected_row_count"] for r in res)})

    def executescript(self, script):
        self._run([{"type": "sequence", "sql": script}])

    def commit(self):
        if self._open:
            self._pipeline([{"type": "execute", "stmt": _stmt("COMMIT")}])
            self._open = False

    def close(self):
        if self._baton is not None:
            # Cerrar el stream descarta cualquier transacción sin confirmar.
            self._pipeline([{"type": "close"}])
            self._baton = None

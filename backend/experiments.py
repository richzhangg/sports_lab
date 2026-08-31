"""
Session-independent storage for saved model runs (SQLite, stdlib only).

A "research instrument" needs experiments to persist across page reloads and
server restarts, so users can build up a comparison set over a real work
session. The full result JSON is stored so a past run can be reopened with all
its charts; the list view returns a lightweight summary.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from typing import Any

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "experiments.db")

_SUMMARY_KEYS = ("spec", "train_metrics", "test_metrics", "diagnostics",
                 "vs_baseline", "overfitting", "cross_validation")


def _conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute(
        """CREATE TABLE IF NOT EXISTS experiments (
               id         TEXT PRIMARY KEY,
               created_at REAL NOT NULL,
               label      TEXT NOT NULL,
               source_key TEXT,
               spec       TEXT NOT NULL,
               result     TEXT NOT NULL
           )"""
    )
    return c


def _summary(row: sqlite3.Row) -> dict[str, Any]:
    result = json.loads(row["result"])
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "label": row["label"],
        "source_key": row["source_key"],
        **{k: result.get(k) for k in _SUMMARY_KEYS},
    }


def save(label: str, result: dict, source_key: str | None) -> dict:
    rid = uuid.uuid4().hex[:12]
    now = time.time()
    with _conn() as c:
        c.execute(
            "INSERT INTO experiments (id, created_at, label, source_key, spec, result) "
            "VALUES (?,?,?,?,?,?)",
            (rid, now, label, source_key, json.dumps(result.get("spec", {})), json.dumps(result)),
        )
        row = c.execute("SELECT * FROM experiments WHERE id=?", (rid,)).fetchone()
    return _summary(row)


def list_all() -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM experiments ORDER BY created_at ASC").fetchall()
    return [_summary(r) for r in rows]


def get(rid: str) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM experiments WHERE id=?", (rid,)).fetchone()
    if not row:
        return None
    out = _summary(row)
    out["result"] = json.loads(row["result"])
    return out


def delete(rid: str) -> bool:
    with _conn() as c:
        cur = c.execute("DELETE FROM experiments WHERE id=?", (rid,))
    return cur.rowcount > 0


def clear() -> int:
    with _conn() as c:
        cur = c.execute("DELETE FROM experiments")
    return cur.rowcount

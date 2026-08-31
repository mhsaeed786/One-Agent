"""Permissions — the consent gate for every sense.

No sensor may import personal context without explicit user permission.
State per sense: pending (default) / granted / denied.
The Mind asks; the user decides; the gate enforces.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from typing import Dict, Optional


class PermissionGate:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "mind.db")
        self.db_path = db_path
        self._init()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self):
        with self._connect() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS sense_permissions (
                sense TEXT PRIMARY KEY,
                state TEXT NOT NULL DEFAULT 'pending',
                granted_at REAL,
                note TEXT DEFAULT ''
            )""")

    def state(self, sense: str) -> str:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT state FROM sense_permissions WHERE sense=?", (sense,)).fetchone()
            return row["state"] if row else "pending"

    def grant(self, sense: str, note: str = "") -> str:
        return self._set(sense, "granted", note)

    def deny(self, sense: str, note: str = "") -> str:
        return self._set(sense, "denied", note)

    def _set(self, sense: str, state: str, note: str) -> str:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO sense_permissions(sense, state, granted_at, note) VALUES (?,?,?,?)"
                " ON CONFLICT(sense) DO UPDATE SET state=excluded.state,"
                " granted_at=excluded.granted_at, note=excluded.note",
                (sense, state, time.time() if state == "granted" else None, note))
        return state

    def all(self) -> Dict[str, str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT sense, state FROM sense_permissions").fetchall()
            return {r["sense"]: r["state"] for r in rows}

    def allowed_senses(self) -> set:
        return {s for s, st in self.all().items() if st == "granted"}

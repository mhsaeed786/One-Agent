"""Anticipation Engine — the Mind notices, proposes, waits for 'yes'.

Core contract:
  1. OBSERVE patterns in absorbed experiences
  2. PROPOSE automations (proposals live in the proposals table)
  3. NOTHING runs until the user says yes (approval gate)
  4. On 'yes', the proposal becomes a scheduled action (cron/bot/sub-app)

This is the instinct loop: feel what the user needs, propose, get go-ahead.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from typing import Dict, List, Optional


# Anticipation rules: (watch-for pattern in experiences) -> (proposal template).
# These grow as the Mind learns. Each proposal is idempotent per signature.
def default_rules() -> List[dict]:
    return [
        {
            "id": "r-teams-recap",
            "if_entity": "teams",
            "min_mentions": 3,
            "title": "Daily Teams pending-task recap",
            "rationale": "You reference Teams task extraction repeatedly in your instructions.",
            "proposal": {
                "kind": "cron",
                "schedule": "0 9 * * *",
                "action": "teams_scrape_merge",
                "desc": "Every morning 9am: scrape Teams pending tasks, MERGE into your existing log (dedupe by date+desc+hours), and brief you.",
            },
        },
        {
            "id": "r-fhir-audit",
            "if_entity": "fhir",
            "min_mentions": 5,
            "title": "Weekly FHIR trigger test audit",
            "rationale": "FHIR is your most-mentioned work topic.",
            "proposal": {
                "kind": "cron",
                "schedule": "0 6 * * 1",
                "action": "fhir_audit",
                "desc": "Every Monday 6am: run FHIR trigger/mapping audit routines and post a summary of inconsistencies found.",
            },
        },
        {
            "id": "r-session-librarian",
            "if_entity": "sessions",
            "min_mentions": 4,
            "title": "Monthly AI-session knowledge digest",
            "rationale": "You constantly import/organize AI sessions — let the Mind digest them monthly.",
            "proposal": {
                "kind": "cron",
                "schedule": "0 7 1 * *",
                "action": "session_digest",
                "desc": "1st of each month: digest new AI-session instructions into knowledge-base files + update the knowledge graph.",
            },
        },
        {
            "id": "r-repo-hygiene",
            "if_entity": "github",
            "min_mentions": 4,
            "title": "Weekly repo hygiene check",
            "rationale": "You care about repos being synced, scrubbed, and green.",
            "proposal": {
                "kind": "cron",
                "schedule": "0 8 * * 6",
                "action": "repo_hygiene",
                "desc": "Every Saturday 8am: check all repos for unpushed changes, unscrubbed secrets, failing tests; report only.",
            },
        },
    ]


class AnticipationEngine:
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
            CREATE TABLE IF NOT EXISTS proposals (
                id TEXT PRIMARY KEY,
                signature TEXT UNIQUE,
                title TEXT,
                rationale TEXT,
                kind TEXT,
                schedule TEXT,
                action TEXT,
                desc TEXT,
                status TEXT DEFAULT 'pending',  -- pending/approved/denied/running
                created_at REAL,
                decided_at REAL
            )""")

    def anticipate(self, store, graph) -> List[dict]:
        """Scan absorbed knowledge; create pending proposals for new patterns."""
        created = []
        with self._connect() as conn:
            for rule in default_rules():
                sig = f"{rule['id']}:{rule['if_entity']}"
                # already proposed?
                if conn.execute("SELECT 1 FROM proposals WHERE signature=?",
                                (sig,)).fetchone():
                    continue
                # enough evidence?
                row = conn.execute(
                    "SELECT count FROM kg_nodes WHERE name=?", (rule["if_entity"],)).fetchone()
                if not row or row["count"] < rule["min_mentions"]:
                    continue
                p = rule["proposal"]
                pid = uuid.uuid4().hex[:12]
                conn.execute(
                    "INSERT INTO proposals(id, signature, title, rationale, kind, schedule, action, desc, status, created_at)"
                    " VALUES (?,?,?,?,?,?,?,?, 'pending', ?)",
                    (pid, sig, rule["title"], rule["rationale"], p["kind"],
                     p["schedule"], p["action"], p["desc"], time.time()))
                created.append({"id": pid, "title": rule["title"], "desc": p["desc"]})
        return created

    def list(self, status: str = None) -> List[dict]:
        with self._connect() as conn:
            if status:
                rows = conn.execute("SELECT * FROM proposals WHERE status=? ORDER BY created_at DESC", (status,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM proposals ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]

    def approve(self, proposal_id: str) -> dict:
        """User said YES. Flip status; the runner picks it up."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM proposals WHERE id=?", (proposal_id,)).fetchone()
            if not row:
                raise KeyError(proposal_id)
            conn.execute("UPDATE proposals SET status='approved', decided_at=? WHERE id=?",
                         (time.time(), proposal_id))
            return dict(row)

    def deny(self, proposal_id: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE proposals SET status='denied', decided_at=? WHERE id=?",
                         (time.time(), proposal_id))

    def stats(self) -> dict:
        with self._connect() as conn:
            rows = conn.execute("SELECT status, COUNT(*) n FROM proposals GROUP BY status").fetchall()
            return {r["status"]: r["n"] for r in rows}

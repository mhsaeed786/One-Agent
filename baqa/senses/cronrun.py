"""Cron Runner — approved proposals become living, recurring automations.

Each minute: check approved proposals, run the ones due, store reports.
Runs are visible at GET /mind/runs. Nothing here ever runs a proposal
that isn't in 'approved' state.

Usage: python -m senses.cronrun   (long-running; pair with the ingest loop)
"""
from __future__ import annotations

import os
import sqlite3
import time
import logging
from typing import List, Sequence

logger = logging.getLogger("mind.cronrun")


def cron_matches(expr: str, now: None = None) -> bool:
    """Minimal 5-field cron matcher: min hour dom mon dow (*, n, a-b, a,b,c)."""
    fields = expr.split()
    if len(fields) != 5:
        return False
    t = time.localtime(time.time() if now is None else now)
    # python tm_wday: Mon=0..Sun=6; cron dow: Sun=0..Sat=6 -> shift by 1
    values = [t.tm_min, t.tm_hour, t.tm_mday, t.tm_mon, (t.tm_wday + 1) % 7]
    for field, value in zip(fields, values):
        if not _field_matches(field, value):
            return False
    return True


def _field_matches(field: str, value: int) -> bool:
    for part in field.split(","):
        if "-" in part and not part.lstrip("-").startswith("-"):
            try:
                lo, hi = part.split("-", 1)
                if int(lo) <= value <= int(hi):
                    return True
            except ValueError:
                continue
        elif part == "*":
            return True
        elif part.startswith("*/"):
            try:
                step = int(part[2:])
                if value % step == 0:
                    return True
            except ValueError:
                continue
        else:
            try:
                if int(part) == value:
                    return True
            except ValueError:
                continue
    return False


class CronRunner:
    def __init__(self, db_path: str = None):
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
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proposal_id TEXT,
                action TEXT,
                ran_at REAL,
                ok INTEGER,
                report TEXT
            )""")

    def due_proposals(self) -> List[sqlite3.Row]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM proposals WHERE status='approved'").fetchall()
            due = []
            for r in rows:
                # avoid double-running within the same minute
                last = conn.execute(
                    "SELECT MAX(ran_at) AS last FROM runs WHERE proposal_id=?", (r["id"],)
                ).fetchone()["last"]
                if last and time.time() - last < 60:
                    continue
                if cron_matches(r["schedule"] or ""):
                    due.append(r)
            return due

    def run_due(self) -> List[dict]:
        from .runner import ACTIONS
        results = []
        for row in self.due_proposals():
            action = row["action"]
            ok, report = 0, {}
            if action in ACTIONS:
                try:
                    report = ACTIONS[action]()
                    ok = 1
                except Exception as e:
                    report = {"error": str(e)[:300]}
            else:
                report = {"error": f"action '{action}' not implemented"}
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO runs(proposal_id, action, ran_at, ok, report)"
                    " VALUES (?,?,?,?,?)",
                    (row["id"], action, time.time(), ok,
                     __import__("json").dumps(report, default=str)))
            results.append({"proposal": row["title"], "action": action,
                            "ok": bool(ok), "report": report})
            logger.info("ran %s -> ok=%s", action, ok)
        return results

    def history(self, limit: int = 20) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM runs ORDER BY ran_at DESC LIMIT ?", (limit,)).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["report"] = __import__("json").loads(d["report"] or "{}")
                out.append(d)
            return out


def run_forever(check_interval_s: int = 60):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [cronrun] %(message)s")
    runner = CronRunner()
    logger.info("cron runner started")
    while True:
        try:
            runner.run_due()
        except Exception as e:
            logger.exception("cycle failed: %s", e)
        time.sleep(check_interval_s)


if __name__ == "__main__":
    run_forever()

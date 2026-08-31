"""Knowledge Graph — grows from absorbed experiences.

Nodes: entities (topics, people-ish keywords, project names).
Edges: co-occurrence within the same experience. Weighted.
"""
from __future__ import annotations

import json
import os
import sqlite3
from typing import Dict, List, Tuple

from .store import ExperienceStore


class KnowledgeGraph:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "mind.db")
        self.db_path = db_path

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def grow_from_store(self, store: ExperienceStore, batch: int = 500) -> int:
        """Build/refresh edges from every experience not yet folded into the graph."""
        with self._connect() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS kg_nodes (
                name TEXT PRIMARY KEY,
                count INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS kg_edges (
                a TEXT NOT NULL,
                b TEXT NOT NULL,
                weight INTEGER DEFAULT 1,
                PRIMARY KEY (a, b)
            );
            """)
            done = conn.execute("SELECT COUNT(*) FROM experiences").fetchone()[0]
            folded = conn.execute("SELECT value FROM meta_kv WHERE key='kg_folded'" ).fetchone() if self._has_meta(conn) else None
            start = int(folded["value"]) if folded else 0

            rows = conn.execute(
                "SELECT rowid, entities FROM experiences WHERE rowid > ? ORDER BY rowid LIMIT ?",
                (start, batch),
            ).fetchall()
            for r in rows:
                ents = json.loads(r["entities"] or "[]")[:10]
                for e in ents:
                    conn.execute(
                        "INSERT INTO kg_nodes(name, count) VALUES(?,1)"
                        " ON CONFLICT(name) DO UPDATE SET count=count+1", (e,))
                for i in range(len(ents)):
                    for j in range(i + 1, len(ents)):
                        a, b = sorted((ents[i].lower(), ents[j].lower()))
                        conn.execute(
                            "INSERT INTO kg_edges(a,b,weight) VALUES(?,?,1)"
                            " ON CONFLICT(a,b) DO UPDATE SET weight=weight+1", (a, b))
            if rows:
                self._set_meta(conn, "kg_folded", str(rows[-1]["rowid"]))
            return len(rows)

    def neighbors(self, node: str, limit: int = 10) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT b AS other, weight FROM kg_edges WHERE a=? "
                "UNION SELECT a AS other, weight FROM kg_edges WHERE b=? "
                "ORDER BY weight DESC LIMIT ?",
                (node.lower(), node.lower(), limit),
            ).fetchall()
            return [{"related": r["other"], "weight": r["weight"]} for r in rows]

    def top_nodes(self, limit: int = 15) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT name, count FROM kg_nodes ORDER BY count DESC LIMIT ?", (limit,)
            ).fetchall()
            return [{"node": r["name"], "mentions": r["count"]} for r in rows]

    def stats(self) -> dict:
        with self._connect() as conn:
            if not conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='kg_nodes'"
            ).fetchone():
                return {"nodes": 0, "edges": 0}
            n = conn.execute("SELECT COUNT(*) FROM kg_nodes").fetchone()[0]
            e = conn.execute("SELECT COUNT(*) FROM kg_edges").fetchone()[0]
            return {"nodes": n, "edges": e}

    def _has_meta(self, conn) -> bool:
        return bool(conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='meta_kv'"
        ).fetchone())

    def _set_meta(self, conn, key: str, value: str):
        conn.execute(
            "CREATE TABLE IF NOT EXISTS meta_kv (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute(
            "INSERT INTO meta_kv(key,value) VALUES(?,?)"
            " ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

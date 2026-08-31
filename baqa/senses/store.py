"""Experience Store — the Mind's memory.

SQLite, FTS5, append-only. Every sensor reading becomes an Experience row.
Deduped by content hash; nothing is ingested twice.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
import re
from dataclasses import dataclass, field, asdict
from typing import Iterable, List, Optional

_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_+-]{2,}")


@dataclass
class Experience:
    """One absorbed moment from a sense."""
    source: str                 # sensor id, e.g. "hermes_sessions", "fs_watch"
    kind: str                   # "chat", "file", "commit", "message", "bookmark", "note", ...
    ts: float                   # unix epoch seconds
    title: str = ""
    text: str = ""
    uri: str = ""               # where it came from (path, url, deep link)
    entities: List[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    @property
    def hash(self) -> str:
        h = hashlib.sha256()
        h.update((self.source + "\x00" + self.kind + "\x00" + self.title + "\x00" + self.text).encode("utf-8", "replace"))
        return h.hexdigest()[:24]

    def to_row(self) -> tuple:
        return (
            self.hash, self.source, self.kind, self.ts, self.title, self.text,
            self.uri, json.dumps(self.entities), json.dumps(self.meta),
        )


class ExperienceStore:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "mind.db")
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS experiences (
                hash TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                kind TEXT NOT NULL,
                ts REAL NOT NULL,
                title TEXT DEFAULT '',
                text TEXT DEFAULT '',
                uri TEXT DEFAULT '',
                entities TEXT DEFAULT '[]',
                meta TEXT DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS ix_exp_source_ts ON experiences(source, ts DESC);
            CREATE VIRTUAL TABLE IF NOT EXISTS experiences_fts USING fts5(
                title, text, content='experiences', content_rowid='rowid'
            );
            CREATE TRIGGER IF NOT EXISTS exp_ai AFTER INSERT ON experiences BEGIN
                INSERT INTO experiences_fts(rowid, title, text)
                VALUES (new.rowid, new.title, new.text);
            END;
            CREATE TRIGGER IF NOT EXISTS exp_ad AFTER DELETE ON experiences BEGIN
                INSERT INTO experiences_fts(experiences_fts, rowid, title, text)
                VALUES ('delete', old.rowid, old.title, old.text);
            END;
            """)
            conn.execute("INSERT OR IGNORE INTO experiences(hash) VALUES ('schema-v1')")

    def absorb(self, experiences: Iterable[Experience]) -> tuple[int, int]:
        """Insert experiences; returns (absorbed, duplicates_skipped)."""
        absorbed = dupes = 0
        with self._connect() as conn:
            for exp in experiences:
                try:
                    conn.execute(
                        "INSERT INTO experiences(hash, source, kind, ts, title, text, uri, entities, meta)"
                        " VALUES (?,?,?,?,?,?,?,?,?)",
                        exp.to_row(),
                    )
                    absorbed += 1
                except sqlite3.IntegrityError:
                    dupes += 1
        return absorbed, dupes

    def search(self, query: str, limit: int = 20) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT e.* FROM experiences_fts f JOIN experiences e ON e.rowid = f.rowid"
                " WHERE experiences_fts MATCH ? ORDER BY rank LIMIT ?",
                (query, limit),
            ).fetchall()
            return [self._row_to_dict(r) for r in rows]

    def recent(self, limit: int = 20, source: Optional[str] = None) -> List[dict]:
        with self._connect() as conn:
            if source:
                rows = conn.execute(
                    "SELECT * FROM experiences WHERE source=? ORDER BY ts DESC LIMIT ?",
                    (source, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM experiences ORDER BY ts DESC LIMIT ?", (limit,)
                ).fetchall()
            return [self._row_to_dict(r) for r in rows]

    def stats(self) -> dict:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM experiences").fetchone()[0]
            by_source = conn.execute(
                "SELECT source, COUNT(*) n FROM experiences GROUP BY source ORDER BY n DESC"
            ).fetchall()
            return {
                "total": total,
                "by_source": {r["source"]: r["n"] for r in by_source},
                "db_path": os.path.abspath(self.db_path),
            }

    def extract_entities(self, text: str, max_entities: int = 12) -> List[str]:
        """Lightweight entity extraction: salient words (no LLM needed)."""
        words = _WORD.findall(text or "")
        stop = {"the", "and", "for", "with", "this", "that", "from", "was", "were",
                "have", "has", "had", "not", "but", "all", "can", "are", "you",
                "his", "her", "its", "into", "out", "get", "got", "new"}
        freq: dict = {}
        for w in words:
            lw = w.lower()
            if lw in stop or len(lw) < 4:
                continue
            freq[lw] = freq.get(lw, 0) + 1
        ranked = sorted(freq.items(), key=lambda kv: -kv[1])
        return [w for w, _ in ranked[:max_entities]]

    @staticmethod
    def _row_to_dict(r) -> dict:
        d = dict(r)
        d["entities"] = json.loads(d.get("entities") or "[]")
        d["meta"] = json.loads(d.get("meta") or "{}")
        return d

"""Sensor: Gemini CLI / Antigravity conversation databases.

Antigravity stores each conversation as a SQLite DB with protobuf-encoded
step payloads. Full proto schemas are undocumented, but user instructions
are embedded as plain UTF-8 strings inside the blobs. We scan blobs for
printable runs (recall-first), filter obvious system scaffolding, and let
hash-dedup handle repeats. Assistant "thinking" text is excluded by the
role-marker heuristic below.
"""
from __future__ import annotations

import glob
import os
import re
import sqlite3
import time
from typing import List

from ..store import Experience

CONV_DIRS = [
    os.path.expanduser(r"~\.gemini\antigravity\conversations"),
]
PRINTABLE = re.compile(rb"[\x20-\x7e]{28,}")
NOISE = ("EPHEMERAL_MESSAGE", "<system>", "system_reminder", "tool_output",
         "command(", "stdout", "stderr", "exited with code")


class GeminiSensor:
    id = "gemini_antigravity"
    description = "Absorbs your instructions from Gemini/Antigravity conversation DBs"

    def available(self) -> bool:
        return any(os.path.isdir(d) for d in CONV_DIRS)

    def poll(self) -> List[Experience]:
        out: List[Experience] = []
        for conv_dir in CONV_DIRS:
            for db in glob.glob(os.path.join(conv_dir, "*.db"))[:100]:
                out.extend(self._absorb_db(db))
        return out

    def _absorb_db(self, db_path: str) -> List[Experience]:
        out: List[Experience] = []
        try:
            conn = sqlite3.connect(db_path)
            # step_type 14 = user turns (verified against live DBs)
            rows = conn.execute(
                "SELECT idx, step_payload FROM steps"
                " WHERE step_type=14 AND step_payload IS NOT NULL").fetchall()
            conn.close()
        except sqlite3.Error:
            return []
        mtime = os.path.getmtime(db_path)
        for idx, blob in rows:
            if not blob:
                continue
            for m in PRINTABLE.finditer(blob):
                text = m.group(0).decode("ascii", "replace").strip().rstrip("\"' ").strip()
                # drop proto length-prefix framing char if it's punctuation
                if text and not text[0].isalnum() and text[0] not in "\"'([-<@#:$%])":
                    text = text[1:].strip()
                if len(text) < 28:
                    continue
                low = text.lower()
                if any(n.lower() in low for n in NOISE):
                    continue
                # human instructions have spaces + normal word structure;
                # proto artifacts are UUIDs, snake_case ids, or hash soup
                words = text.split()
                if len(words) < 4:
                    continue
                if text.count("-") > 3:          # uuid fragments
                    continue
                snake = sum(1 for w in words if "_" in w and w.islower())
                if snake >= len(words) - 1 and snake > 0:
                    continue
                if sum(c.isdigit() for c in text) > len(text) * 0.3:
                    continue
                if re.match(r"^\d+:\s", text):   # line-numbered dumps
                    continue
                out.append(Experience(
                    source="ai_session:gemini",
                    kind="instruction",
                    ts=mtime,
                    title=text[:90],
                    text=text[:3000],
                    uri=f"{os.path.basename(db_path)}#step{idx}",
                ))
        return out

"""Rebuild the AI Session Hub database from the reliable Hermes state.db.

The existing session_hub.db used an old, lossy schema (truncated content,
raw table dumps) that no longer matches schema.sql, so the app crashes on
start. This rebuilds a fresh hub DB from Hermes' state.db — the single
authoritative store holding complete transcripts for the KEPT sessions
(goose, claude-code, antigravity-cli, desktop).
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone

HUB_DIR = r"C:\Users\hassan.saeed\ai-session-hub"
HERMES_DB = r"C:\Users\hassan.saeed\AppData\Local\hermes\state.db"
HUB_DB = os.path.join(HUB_DIR, "db", "session_hub.db")
SCHEMA = os.path.join(HUB_DIR, "db", "schema.sql")

# Map Hermes source -> hub tool entry
TOOLS = [
    ("goose", "Goose"),
    ("claude-code", "Claude Code"),
    ("antigravity-cli", "Antigravity CLI"),
    ("desktop", "Hermes Desktop"),
]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def main():
    # 1. Recreate hub DB from schema.sql
    if os.path.exists(HUB_DB):
        os.remove(HUB_DB)
    with open(SCHEMA, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    conn = sqlite3.connect(HUB_DB)
    conn.executescript(schema_sql)

    # 2. Register tools
    for name, display in TOOLS:
        conn.execute(
            "INSERT OR IGNORE INTO tools (name, display_name, adapter_class, data_path, enabled) "
            "VALUES (?, ?, ?, ?, 1)",
            (name, display, "StubAdapter", None),
        )

    # 3. Read Hermes state.db sessions
    h = sqlite3.connect(f"file:{HERMES_DB}?mode=ro", uri=True)
    h.row_factory = sqlite3.Row
    hc = h.cursor()
    hc.execute(
        "SELECT id, source, title, cwd, model, started_at, ended_at, origin_json "
        "FROM sessions WHERE source IN ('goose','claude-code','antigravity-cli','desktop')"
    )
    hermes_sessions = hc.fetchall()
    print(f"Reading {len(hermes_sessions)} sessions from Hermes state.db")

    imported_sessions = 0
    imported_messages = 0

    for hs in hermes_sessions:
        source = hs["source"]
        tool_name = source  # matches TOOLS names
        sid = hs["id"]

        # messages
        hc.execute(
            "SELECT id, role, content, timestamp, tool_name FROM messages "
            "WHERE session_id=? ORDER BY id",
            (sid,),
        )
        msgs = hc.fetchall()

        hub_sid = f"{tool_name}:{sid}"
        started = datetime.fromtimestamp(hs["started_at"], timezone.utc).isoformat() if hs["started_at"] else None
        ended = datetime.fromtimestamp(hs["ended_at"], timezone.utc).isoformat() if hs["ended_at"] else None
        title = hs["title"] or "Untitled"

        conn.execute(
            """INSERT INTO sessions (id, tool, session_id, title, project_path, model,
               status, started_at, ended_at, message_count, file_path, file_size_bytes,
               file_mtime, raw_metadata, first_synced_at, last_synced_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (hub_sid, tool_name, sid, title, hs["cwd"], hs["model"], "completed",
             started, ended, len(msgs), None, None, None, None, now_iso(), now_iso()),
        )

        for seq, m in enumerate(msgs):
            content = m["content"] or ""
            ts = None
            if m["timestamp"]:
                try:
                    ts = datetime.fromtimestamp(m["timestamp"], timezone.utc).isoformat()
                except (TypeError, ValueError):
                    ts = None
            conn.execute(
                """INSERT INTO messages (session_fk, message_id, role, content_text,
                   content_type, model, timestamp, token_input, token_output,
                   raw_json, parent_id, seq)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (hub_sid, None, m["role"], content, "text", hs["model"], ts,
                 None, None, None, None, seq),
            )
            imported_messages += 1

        imported_sessions += 1

    h.close()

    # update tool stats
    for name, _ in TOOLS:
        n = conn.execute("SELECT COUNT(*) FROM sessions WHERE tool=?", (name,)).fetchone()[0]
        conn.execute(
            "UPDATE tools SET last_sync_at=?, session_count=? WHERE name=?",
            (now_iso(), n, name),
        )

    conn.commit()
    conn.close()
    print(f"Rebuilt hub DB: {imported_sessions} sessions, {imported_messages} messages")
    print(f"Hub DB at: {HUB_DB}")


if __name__ == "__main__":
    main()

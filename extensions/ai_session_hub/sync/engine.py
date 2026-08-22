"""Sync engine — orchestrates incremental sync across all tool adapters."""

import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from typing import Generator

from config import DB_PATH, TOOL_CONFIGS, get_adapter
from adapters.base import ParsedSession, ParsedMessage


class SyncEngine:
    """Runs incremental sync for all registered tools.

    Strategy:
    - For each enabled tool, create its adapter and call discover_sessions().
    - Compare discovered sessions against existing DB records by composite ID (tool:session_id).
    - If a session is new or its file mtime/size changed, re-parse its messages.
    - Track sync progress in sync_log table.
    """

    def __init__(self, force_full: bool = False):
        self.force_full = force_full
        self.conn = self._get_connection()
        self.results = {}

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        return conn

    def run_all(self) -> dict:
        """Run sync for all enabled tools. Returns {tool_name: stats}."""
        tools = self.conn.execute(
            "SELECT name, enabled FROM tools WHERE enabled = 1"
        ).fetchall()

        for tool in tools:
            tool_name = tool["name"]
            try:
                self.results[tool_name] = self._sync_tool(tool_name)
            except Exception as e:
                self.results[tool_name] = {
                    "status": "error",
                    "error": str(e),
                    "found": 0,
                    "new": 0,
                    "updated": 0,
                }
                print(f"  [!] {tool_name}: ERROR - {e}")

        self.conn.close()
        return self.results

    def _sync_tool(self, tool_name: str) -> dict:
        """Sync a single tool. Returns stats dict."""
        started = datetime.now(timezone.utc).isoformat()
        log_id = self._start_sync_log(tool_name, started)

        adapter = get_adapter(tool_name)
        if adapter is None:
            self._finish_sync_log(log_id, "skipped", error="No adapter")
            return {"status": "skipped", "found": 0, "new": 0, "updated": 0}

        print(f"  [*] {tool_name}: discovering sessions...")

        # Check availability
        if not adapter.is_available():
            self._finish_sync_log(log_id, "unavailable", error="Data path not accessible")
            print(f"  [-] {tool_name}: data path not available")
            return {"status": "unavailable", "found": 0, "new": 0, "updated": 0}

        found = 0
        new = 0
        updated = 0
        errors = 0

        try:
            for session in adapter.discover_sessions():
                found += 1
                composite_id = f"{tool_name}:{session.session_id}"

                # Check if we need to sync this session
                action = self._should_sync(composite_id, session)
                if action == "skip":
                    continue

                try:
                    # Parse messages
                    messages = list(adapter.parse_messages(session))
                    msg_count = len(messages)

                    # Upsert session
                    self._upsert_session(tool_name, composite_id, session, msg_count)

                    # Delete old messages and re-insert
                    self.conn.execute(
                        "DELETE FROM messages WHERE session_fk = ?", (composite_id,)
                    )
                    self._insert_messages(composite_id, messages)

                    self.conn.commit()

                    if action == "new":
                        new += 1
                    else:
                        updated += 1

                except Exception as e:
                    errors += 1
                    print(f"    [!] Error syncing {session.session_id}: {e}")
                    continue

        except Exception as e:
            self._finish_sync_log(log_id, "error", error=str(e))
            return {"status": "error", "error": str(e), "found": found, "new": new, "updated": updated}

        # Update tool stats
        self._update_tool_stats(tool_name, found)

        status = "ok" if errors == 0 else f"ok ({errors} errors)"
        self._finish_sync_log(
            log_id, status,
            sessions_found=found, sessions_new=new, sessions_updated=updated
        )

        print(f"  [+] {tool_name}: found={found} new={new} updated={updated}")
        return {"status": status, "found": found, "new": new, "updated": updated}

    def _should_sync(self, composite_id: str, session: ParsedSession) -> str:
        """Determine if a session needs syncing. Returns 'new', 'update', or 'skip'."""
        if self.force_full:
            return "update" if self._session_exists(composite_id) else "new"

        row = self.conn.execute(
            "SELECT file_size_bytes, file_mtime FROM sessions WHERE id = ?",
            (composite_id,)
        ).fetchone()

        if row is None:
            return "new"

        # Compare mtime and size for incremental check
        if (row["file_size_bytes"] != session.file_size_bytes or
                row["file_mtime"] != session.file_mtime):
            return "update"

        return "skip"

    def _session_exists(self, composite_id: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM sessions WHERE id = ?", (composite_id,)
        ).fetchone()
        return row is not None

    def _upsert_session(self, tool_name: str, composite_id: str,
                        session: ParsedSession, msg_count: int):
        """Insert or update a session record."""
        raw_meta = json.dumps(session.raw_metadata) if session.raw_metadata else None
        now = datetime.now(timezone.utc).isoformat()

        existing = self.conn.execute(
            "SELECT 1 FROM sessions WHERE id = ?", (composite_id,)
        ).fetchone()

        if existing:
            self.conn.execute("""
                UPDATE sessions SET
                    title = ?, project_path = ?, model = ?, status = ?,
                    started_at = ?, ended_at = ?, message_count = ?,
                    file_path = ?, file_size_bytes = ?, file_mtime = ?,
                    raw_metadata = ?, last_synced_at = ?
                WHERE id = ?
            """, (
                session.title, session.project_path, session.model, session.status,
                session.started_at, session.ended_at, msg_count,
                session.file_path, session.file_size_bytes, session.file_mtime,
                raw_meta, now, composite_id
            ))
        else:
            self.conn.execute("""
                INSERT INTO sessions (
                    id, tool, session_id, title, project_path, model, status,
                    started_at, ended_at, message_count, file_path,
                    file_size_bytes, file_mtime, raw_metadata, first_synced_at, last_synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                composite_id, tool_name, session.session_id, session.title,
                session.project_path, session.model, session.status,
                session.started_at, session.ended_at, msg_count, session.file_path,
                session.file_size_bytes, session.file_mtime, raw_meta, now, now
            ))

    def _insert_messages(self, composite_id: str, messages: list):
        """Batch insert messages for a session."""
        for msg in messages:
            raw_json = json.dumps(msg.raw_json) if msg.raw_json else None
            self.conn.execute("""
                INSERT INTO messages (
                    session_fk, message_id, role, content_text, content_type,
                    model, timestamp, token_input, token_output, raw_json, parent_id, seq
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                composite_id, msg.message_id, msg.role, msg.content_text,
                msg.content_type, msg.model, msg.timestamp,
                msg.token_input, msg.token_output, raw_json,
                msg.parent_id, msg.seq
            ))

    def _start_sync_log(self, tool_name: str, started: str) -> int:
        cursor = self.conn.execute(
            """INSERT INTO sync_log (tool, sync_started_at, status)
               VALUES (?, ?, 'running')""",
            (tool_name, started)
        )
        self.conn.commit()
        return cursor.lastrowid

    def _finish_sync_log(self, log_id: int, status: str,
                         sessions_found: int = 0, sessions_new: int = 0,
                         sessions_updated: int = 0, error: str = None):
        ended = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """UPDATE sync_log SET
                sync_ended_at = ?, status = ?,
                sessions_found = ?, sessions_new = ?, sessions_updated = ?,
                error_message = ?
            WHERE id = ?""",
            (ended, status, sessions_found, sessions_new, sessions_updated, error, log_id)
        )
        self.conn.commit()

    def _update_tool_stats(self, tool_name: str, session_count: int):
        total_size = self.conn.execute(
            "SELECT COALESCE(SUM(file_size_bytes), 0) FROM sessions WHERE tool = ?",
            (tool_name,)
        ).fetchone()[0]
        count = self.conn.execute(
            "SELECT COUNT(*) FROM sessions WHERE tool = ?",
            (tool_name,)
        ).fetchone()[0]

        self.conn.execute(
            """UPDATE tools SET last_sync_at = ?, session_count = ?, total_size_mb = ?
               WHERE name = ?""",
            (datetime.now(timezone.utc).isoformat(), count, round(total_size / 1048576, 2), tool_name)
        )
        self.conn.commit()

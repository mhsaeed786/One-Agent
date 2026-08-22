"""Gemini CLI adapter — parses ~/.gemini/antigravity-cli/ history."""

import os
from datetime import datetime, timezone
from typing import Generator

from adapters.base import BaseAdapter, ParsedSession, ParsedMessage


class GeminiCliAdapter(BaseAdapter):
    TOOL_NAME = "gemini_cli"
    DISPLAY_NAME = "Gemini CLI"

    def discover_sessions(self) -> Generator[ParsedSession, None, None]:
        """Parse history.jsonl for Gemini CLI sessions."""
        history_path = os.path.join(self.data_path, "history.jsonl")
        if not os.path.isfile(history_path):
            return

        # Group entries by conversationId
        conversations = {}
        for raw in self._safe_read_jsonl(history_path):
            conv_id = raw.get("conversationId", "unknown")
            if conv_id not in conversations:
                conversations[conv_id] = []
            conversations[conv_id].append(raw)

        for conv_id, entries in conversations.items():
            if not entries:
                continue

            first = entries[0]
            last = entries[-1]
            display = first.get("display", "")
            workspace = first.get("workspace", "")

            ts_ms = first.get("timestamp")
            started = None
            if isinstance(ts_ms, (int, float)):
                started = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat()

            # Count .pb conversation files
            conv_dir = os.path.join(self.data_path, "conversations")
            pb_count = 0
            if os.path.isdir(conv_dir):
                pb_count = len([f for f in os.listdir(conv_dir) if f.endswith(".pb")])

            yield ParsedSession(
                session_id=conv_id,
                title=self._truncate(display, 200) if display else f"Gemini CLI ({conv_id[:8]})",
                project_path=workspace or None,
                model="gemini",
                status="completed",
                started_at=started,
                ended_at=None,
                file_path=history_path,
                file_size_bytes=0,
                file_mtime=0.0,
                raw_metadata={
                    "entry_count": len(entries),
                    "pb_files_available": pb_count,
                    "note": "Full conversations in .pb format (protobuf/encrypted) - content not extractable",
                },
            )

    def parse_messages(self, session: ParsedSession) -> Generator[ParsedMessage, None, None]:
        """Parse history entries as user prompts (no assistant responses available)."""
        seq = 0
        for raw in self._safe_read_jsonl(session.file_path):
            conv_id = raw.get("conversationId", "unknown")
            if conv_id != session.session_id and session.session_id != "unknown":
                continue

            display = raw.get("display", "")
            if not display:
                continue

            ts_ms = raw.get("timestamp")
            ts = None
            if isinstance(ts_ms, (int, float)):
                ts = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat()

            seq += 1
            yield ParsedMessage(
                message_id=None,
                role="user",
                content_text=self._truncate(display, 5000),
                content_type="text",
                model="gemini",
                timestamp=ts,
                seq=seq,
            )

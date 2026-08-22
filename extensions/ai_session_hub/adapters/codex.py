"""Codex session adapter — parses ~/.codex/sessions/ JSONL files."""

import json
import os
from typing import Generator

from adapters.base import BaseAdapter, ParsedSession, ParsedMessage


class CodexAdapter(BaseAdapter):
    TOOL_NAME = "codex"
    DISPLAY_NAME = "Codex"

    def discover_sessions(self) -> Generator[ParsedSession, None, None]:
        """Walk ~/.codex/sessions/YYYY/MM/DD/ for rollout JSONL files."""
        sessions_dir = os.path.join(self.data_path, "sessions")
        if not os.path.isdir(sessions_dir):
            return

        for root, _dirs, files in os.walk(sessions_dir):
            for fname in files:
                if not fname.startswith("rollout-") or not fname.endswith(".jsonl"):
                    continue
                fpath = os.path.join(root, fname)
                stat = os.stat(fpath)

                # Extract session ID from filename
                # rollout-2026-03-03T01-20-42-019cb25b-...-.jsonl
                session_id = fname.replace("rollout-", "").replace(".jsonl", "")

                yield ParsedSession(
                    session_id=session_id,
                    title=None,  # extracted during parse
                    project_path=None,  # extracted from session_meta
                    model=None,  # extracted from session_meta
                    status="completed",
                    started_at=None,
                    ended_at=None,
                    file_path=fpath,
                    file_size_bytes=stat.st_size,
                    file_mtime=stat.st_mtime,
                    raw_metadata=None,
                )

    def parse_messages(self, session: ParsedSession) -> Generator[ParsedMessage, None, None]:
        """Parse Codex rollout JSONL into messages."""
        seq = 0
        first_user_extracted = False

        for raw in self._safe_read_jsonl(session.file_path):
            msg_type = raw.get("type", "")

            if msg_type == "session_meta":
                payload = raw.get("payload", {})
                session.project_path = payload.get("cwd")
                session.model = payload.get("model_provider")
                session.started_at = raw.get("timestamp") or payload.get("timestamp")
                session.raw_metadata = {
                    "cli_version": payload.get("cli_version"),
                    "source": payload.get("source"),
                    "originator": payload.get("originator"),
                }

            elif msg_type == "response_item":
                payload = raw.get("payload", {})
                role = payload.get("role", "unknown")
                content_blocks = payload.get("content") or []

                if isinstance(content_blocks, str):
                    content_blocks = [{"type": "text", "text": content_blocks}]

                if not isinstance(content_blocks, list):
                    content_blocks = []

                for block in content_blocks:
                    if not isinstance(block, dict):
                        continue
                    text = block.get("text", "")
                    if not text:
                        continue

                    # Extract title from first user message
                    if not first_user_extracted and role == "user" and text:
                        session.title = self._truncate(text, 200)
                        first_user_extracted = True

                    seq += 1
                    yield ParsedMessage(
                        message_id=payload.get("id"),
                        role=role if role in ("user", "assistant", "system") else "assistant",
                        content_text=self._truncate(text, 5000),
                        content_type=block.get("type", "text"),
                        model=session.model,
                        timestamp=raw.get("timestamp"),
                        seq=seq,
                    )

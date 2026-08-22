"""Cursor adapter — parses ~/.cursor/projects/*/agent-transcripts/ JSONL files."""

import json
import os
from typing import Generator

from adapters.base import BaseAdapter, ParsedSession, ParsedMessage


class CursorAdapter(BaseAdapter):
    TOOL_NAME = "cursor"
    DISPLAY_NAME = "Cursor"

    def discover_sessions(self) -> Generator[ParsedSession, None, None]:
        """Walk ~/.cursor/projects/*/agent-transcripts/ for JSONL files."""
        projects_dir = os.path.join(self.data_path, "projects")
        if not os.path.isdir(projects_dir):
            return

        for proj_dir_name in os.listdir(projects_dir):
            proj_path = os.path.join(projects_dir, proj_dir_name)
            if not os.path.isdir(proj_path):
                continue

            transcripts_dir = os.path.join(proj_path, "agent-transcripts")
            if not os.path.isdir(transcripts_dir):
                continue

            for session_dir in os.listdir(transcripts_dir):
                session_path = os.path.join(transcripts_dir, session_dir)
                if not os.path.isdir(session_path):
                    continue

                for fname in os.listdir(session_path):
                    if not fname.endswith(".jsonl"):
                        continue
                    fpath = os.path.join(session_path, fname)
                    session_id = fname.replace(".jsonl", "")
                    stat = os.stat(fpath)

                    yield ParsedSession(
                        session_id=session_id,
                        title=None,
                        project_path=proj_dir_name,
                        model=None,
                        status="completed",
                        started_at=None,
                        ended_at=None,
                        file_path=fpath,
                        file_size_bytes=stat.st_size,
                        file_mtime=stat.st_mtime,
                        raw_metadata={"project_dir": proj_dir_name},
                    )

    def parse_messages(self, session: ParsedSession) -> Generator[ParsedMessage, None, None]:
        """Parse Cursor agent-transcript JSONL into messages."""
        seq = 0
        first_user_extracted = session.title is not None

        for raw in self._safe_read_jsonl(session.file_path):
            role = raw.get("role", "")
            message = raw.get("message", {})

            if not message:
                continue

            content_blocks = message.get("content", [])
            if isinstance(content_blocks, str):
                content_blocks = [{"type": "text", "text": content_blocks}]

            for block in content_blocks:
                if not isinstance(block, dict):
                    continue

                block_type = block.get("type", "text")
                text = block.get("text", "")

                if block_type == "tool_use":
                    text = f"Tool: {block.get('name', 'unknown')}\n{json.dumps(block.get('input', {}), indent=2)[:2000]}"
                elif block_type == "tool_result":
                    text = block.get("content", "") if isinstance(block.get("content"), str) else str(block.get("content", ""))[:2000]

                if not text:
                    continue

                if not first_user_extracted and role == "user":
                    session.title = self._truncate(text, 200)
                    first_user_extracted = True

                seq += 1
                yield ParsedMessage(
                    message_id=raw.get("uuid"),
                    role=role if role in ("user", "assistant", "system") else "assistant",
                    content_text=self._truncate(text, 5000),
                    content_type=block_type,
                    model=message.get("model"),
                    timestamp=raw.get("timestamp"),
                    seq=seq,
                )

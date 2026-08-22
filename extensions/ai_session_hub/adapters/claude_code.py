"""Claude Code session adapter — parses ~/.claude/projects/*/ JSONL files."""

import json
import os
from typing import Generator

from adapters.base import BaseAdapter, ParsedSession, ParsedMessage


class ClaudeCodeAdapter(BaseAdapter):
    TOOL_NAME = "claude_code"
    DISPLAY_NAME = "Claude Code"

    def discover_sessions(self) -> Generator[ParsedSession, None, None]:
        """Walk ~/.claude/projects/ for JSONL session files."""
        projects_dir = os.path.join(self.data_path, "projects")
        if not os.path.isdir(projects_dir):
            return

        # Load session metadata from sessions/*.json
        session_meta = self._load_session_metadata()

        for proj_dir_name in os.listdir(projects_dir):
            proj_path = os.path.join(projects_dir, proj_dir_name)
            if not os.path.isdir(proj_path):
                continue

            # Decode the project directory name back to a path
            project_path = proj_dir_name.replace("-", os.sep)
            if project_path.startswith("C" + os.sep):
                project_path = project_path.replace(os.sep, os.sep, 1)
                project_path = project_path[:2] + ":" + project_path[2:]

            for fname in os.listdir(proj_path):
                if not fname.endswith(".jsonl"):
                    continue
                fpath = os.path.join(proj_path, fname)
                session_id = fname.replace(".jsonl", "")

                # Try to get enhanced metadata
                meta = session_meta.get(session_id, {})
                stat = os.stat(fpath)

                # Extract title from first summary or first user message
                title = meta.get("title")

                yield ParsedSession(
                    session_id=session_id,
                    title=title,
                    project_path=meta.get("cwd", project_path),
                    model=meta.get("version"),
                    status="completed",
                    started_at=meta.get("startedAt"),
                    ended_at=meta.get("updatedAt"),
                    file_path=fpath,
                    file_size_bytes=stat.st_size,
                    file_mtime=stat.st_mtime,
                    raw_metadata={"project_dir": proj_dir_name},
                )

    def parse_messages(self, session: ParsedSession) -> Generator[ParsedMessage, None, None]:
        """Parse Claude Code JSONL session into messages."""
        seq = 0
        title_extracted = session.title is not None

        for raw in self._safe_read_jsonl(session.file_path):
            msg_type = raw.get("type", "")

            if msg_type == "user":
                msg = raw.get("message", {})
                content = msg.get("content", "")
                if isinstance(content, list):
                    # Tool results — extract text portions
                    texts = []
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                texts.append(block.get("text", ""))
                            elif block.get("type") == "tool_result":
                                for sub in block.get("content", []):
                                    if isinstance(sub, dict) and sub.get("type") == "text":
                                        texts.append(sub.get("text", ""))
                    content = "\n".join(texts)
                elif isinstance(content, str):
                    content = content

                # Extract title from first user message if not already set
                if not title_extracted and content:
                    session.title = self._truncate(content, 200)
                    title_extracted = True

                seq += 1
                yield ParsedMessage(
                    message_id=raw.get("uuid"),
                    role="user",
                    content_text=self._truncate(content, 5000),
                    content_type="text",
                    timestamp=raw.get("timestamp"),
                    raw_json=raw,
                    parent_id=raw.get("parentUuid"),
                    seq=seq,
                )

            elif msg_type == "assistant":
                msg = raw.get("message", {})
                model = msg.get("model", "")
                content_blocks = msg.get("content", [])
                usage = msg.get("usage", {})

                for block in content_blocks:
                    if not isinstance(block, dict):
                        continue
                    block_type = block.get("type", "text")

                    if block_type == "thinking":
                        seq += 1
                        yield ParsedMessage(
                            message_id=raw.get("uuid"),
                            role="assistant",
                            content_text=self._truncate(block.get("thinking", ""), 5000),
                            content_type="thinking",
                            model=model,
                            timestamp=raw.get("timestamp"),
                            token_input=usage.get("input_tokens"),
                            token_output=usage.get("output_tokens"),
                            parent_id=raw.get("parentUuid"),
                            seq=seq,
                        )
                    elif block_type == "text":
                        seq += 1
                        yield ParsedMessage(
                            message_id=raw.get("uuid"),
                            role="assistant",
                            content_text=self._truncate(block.get("text", ""), 5000),
                            content_type="text",
                            model=model,
                            timestamp=raw.get("timestamp"),
                            token_input=usage.get("input_tokens"),
                            token_output=usage.get("output_tokens"),
                            parent_id=raw.get("parentUuid"),
                            seq=seq,
                        )
                    elif block_type == "tool_use":
                        seq += 1
                        yield ParsedMessage(
                            message_id=raw.get("uuid"),
                            role="assistant",
                            content_text=self._truncate(
                                json.dumps(block.get("input", {})), 2000
                            ),
                            content_type="tool_use",
                            model=model,
                            timestamp=raw.get("timestamp"),
                            token_input=usage.get("input_tokens"),
                            token_output=usage.get("output_tokens"),
                            raw_json=block,
                            parent_id=raw.get("parentUuid"),
                            seq=seq,
                        )

            elif msg_type == "summary" and not session.title:
                text = raw.get("summary", "")
                if text:
                    session.title = self._truncate(text, 200)

    def _load_session_metadata(self) -> dict:
        """Load session metadata from ~/.claude/sessions/*.json and history.jsonl."""
        meta = {}
        sessions_dir = os.path.join(self.data_path, "sessions")
        if os.path.isdir(sessions_dir):
            for fname in os.listdir(sessions_dir):
                if not fname.endswith(".json"):
                    continue
                fpath = os.path.join(sessions_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    sid = data.get("sessionId", fname.replace(".json", ""))
                    meta[sid] = {
                        "title": None,
                        "cwd": data.get("cwd"),
                        "startedAt": self._ms_to_iso(data.get("startedAt")),
                        "updatedAt": None,
                        "version": data.get("version"),
                    }
                except (json.JSONDecodeError, OSError):
                    continue

        # Also parse history.jsonl for lightweight metadata
        history_path = os.path.join(self.data_path, "history.jsonl")
        if os.path.isfile(history_path):
            for raw in self._safe_read_jsonl(history_path):
                sid = raw.get("sessionId")
                if sid and sid not in meta:
                    meta[sid] = {
                        "title": self._truncate(raw.get("display", ""), 200),
                        "cwd": raw.get("cwd"),
                        "startedAt": raw.get("timestamp"),
                        "updatedAt": raw.get("timestamp"),
                        "version": None,
                    }

        return meta

    @staticmethod
    def _ms_to_iso(val) -> str | None:
        """Convert millisecond timestamp to ISO format."""
        if not val:
            return None
        try:
            from datetime import datetime, timezone
            dt = datetime.fromtimestamp(val / 1000, tz=timezone.utc)
            return dt.isoformat()
        except (TypeError, ValueError, OSError):
            return str(val) if val else None

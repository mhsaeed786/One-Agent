"""CommandCode session adapter — parses ~/.commandcode/ JSONL files."""

import json
import os
from typing import Generator

from adapters.base import BaseAdapter, ParsedSession, ParsedMessage


class CommandCodeAdapter(BaseAdapter):
    TOOL_NAME = "commandcode"
    DISPLAY_NAME = "CommandCode"

    def discover_sessions(self) -> Generator[ParsedSession, None, None]:
        """Walk ~/.commandcode/projects/ for JSONL session files."""
        projects_dir = os.path.join(self.data_path, "projects")
        if not os.path.isdir(projects_dir):
            # Fall back to history.jsonl only
            yield from self._discover_from_history()
            return

        for proj_dir_name in os.listdir(projects_dir):
            proj_path = os.path.join(projects_dir, proj_dir_name)
            if not os.path.isdir(proj_path):
                continue

            for fname in os.listdir(proj_path):
                if not fname.endswith(".jsonl"):
                    continue
                fpath = os.path.join(proj_path, fname)
                session_id = fname.replace(".jsonl", "")
                stat = os.stat(fpath)

                # Check for companion .meta.json
                meta_path = fpath.replace(".jsonl", ".meta.json")
                meta = {}
                if os.path.isfile(meta_path):
                    try:
                        with open(meta_path, "r", encoding="utf-8") as f:
                            meta = json.load(f)
                    except (json.JSONDecodeError, OSError):
                        pass

                yield ParsedSession(
                    session_id=session_id,
                    title=meta.get("title"),
                    project_path=proj_dir_name,
                    model=meta.get("model"),
                    status="completed",
                    started_at=meta.get("startedAt"),
                    ended_at=meta.get("updatedAt"),
                    file_path=fpath,
                    file_size_bytes=stat.st_size,
                    file_mtime=stat.st_mtime,
                    raw_metadata=meta or None,
                )

        # Also yield from history.jsonl
        yield from self._discover_from_history()

    def _discover_from_history(self) -> Generator[ParsedSession, None, None]:
        """Parse history.jsonl as lightweight session entries."""
        history_path = os.path.join(self.data_path, "history.jsonl")
        if not os.path.isfile(history_path):
            return

        stat = os.stat(history_path)
        # Use history.jsonl as a single session with all prompts
        yield ParsedSession(
            session_id="history",
            title="CommandCode History",
            project_path=None,
            model=None,
            status="completed",
            started_at=None,
            ended_at=None,
            file_path=history_path,
            file_size_bytes=stat.st_size,
            file_mtime=stat.st_mtime,
            raw_metadata={"source": "history.jsonl"},
        )

    def parse_messages(self, session: ParsedSession) -> Generator[ParsedMessage, None, None]:
        """Parse CommandCode JSONL messages."""
        seq = 0
        first_user_extracted = session.title is not None

        for raw in self._safe_read_jsonl(session.file_path):
            # Format 1: history.jsonl with {"p":"text","t":timestamp_ms}
            if "p" in raw and "t" in raw:
                text = raw.get("p", "")
                if not text:
                    continue

                if not first_user_extracted:
                    session.title = self._truncate(text, 200)
                    first_user_extracted = True

                seq += 1
                ts = raw.get("t")
                if isinstance(ts, (int, float)):
                    from datetime import datetime, timezone
                    ts = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat()

                yield ParsedMessage(
                    message_id=None,
                    role="user",
                    content_text=self._truncate(text, 5000),
                    content_type="text",
                    timestamp=ts,
                    seq=seq,
                )
                continue

            # Format 2: session JSONL with role/content structure (Claude-like)
            msg_type = raw.get("type", "")
            role = raw.get("role", "")

            if msg_type == "user" or role == "user":
                content = raw.get("message", {}).get("content", "")
                if isinstance(content, str):
                    pass
                elif isinstance(content, list):
                    texts = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            texts.append(block.get("text", ""))
                    content = "\n".join(texts)

                if not first_user_extracted and content:
                    session.title = self._truncate(content, 200)
                    first_user_extracted = True

                seq += 1
                yield ParsedMessage(
                    message_id=raw.get("uuid"),
                    role="user",
                    content_text=self._truncate(content, 5000),
                    content_type="text",
                    timestamp=raw.get("timestamp"),
                    parent_id=raw.get("parentUuid"),
                    seq=seq,
                )

            elif msg_type == "assistant" or role == "assistant":
                msg = raw.get("message", {})
                content_blocks = msg.get("content", [])
                if isinstance(content_blocks, str):
                    content_blocks = [{"type": "text", "text": content_blocks}]

                for block in content_blocks:
                    if not isinstance(block, dict):
                        continue
                    text = block.get("text", "") or block.get("thinking", "")
                    if not text:
                        continue

                    seq += 1
                    yield ParsedMessage(
                        message_id=raw.get("uuid"),
                        role="assistant",
                        content_text=self._truncate(text, 5000),
                        content_type=block.get("type", "text"),
                        model=msg.get("model"),
                        timestamp=raw.get("timestamp"),
                        parent_id=raw.get("parentUuid"),
                        seq=seq,
                    )

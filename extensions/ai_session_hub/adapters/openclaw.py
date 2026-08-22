"""OpenClaw adapter — parses ~/.openclaw/ workspace and knowledge docs."""

import json
import os
from typing import Generator

from adapters.base import BaseAdapter, ParsedSession, ParsedMessage


class OpenClawAdapter(BaseAdapter):
    TOOL_NAME = "openclaw"
    DISPLAY_NAME = "OpenClaw"

    def discover_sessions(self) -> Generator[ParsedSession, None, None]:
        """Walk ~/.openclaw/ for session and knowledge data."""
        if not os.path.isdir(self.data_path):
            return

        # Check for sessions directory
        sessions_dir = os.path.join(self.data_path, "sessions")
        if os.path.isdir(sessions_dir):
            for fname in os.listdir(sessions_dir):
                fpath = os.path.join(sessions_dir, fname)
                if not os.path.isfile(fpath):
                    continue
                if fname.endswith((".json", ".jsonl", ".md")):
                    stat = os.stat(fpath)
                    yield ParsedSession(
                        session_id=fname,
                        title=f"OpenClaw Session: {fname}",
                        project_path=None,
                        model=None,
                        status="completed",
                        started_at=None,
                        ended_at=None,
                        file_path=fpath,
                        file_size_bytes=stat.st_size,
                        file_mtime=stat.st_mtime,
                        raw_metadata={"source": "sessions"},
                    )

        # Check for knowledge base / workspace docs
        knowledge_dir = os.path.join(self.data_path, "knowledge")
        if os.path.isdir(knowledge_dir):
            for root, _dirs, files in os.walk(knowledge_dir):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    if fname.endswith((".json", ".jsonl", ".md", ".txt")):
                        stat = os.stat(fpath)
                        yield ParsedSession(
                            session_id=f"kb_{fname}",
                            title=f"OpenClaw Knowledge: {fname}",
                            project_path=None,
                            model=None,
                            status="completed",
                            started_at=None,
                            ended_at=None,
                            file_path=fpath,
                            file_size_bytes=stat.st_size,
                            file_mtime=stat.st_mtime,
                            raw_metadata={"source": "knowledge"},
                        )

        # Check for config files
        for config_name in ("config.json", "settings.json", "state.json"):
            config_path = os.path.join(self.data_path, config_name)
            if os.path.isfile(config_path):
                stat = os.stat(config_path)
                yield ParsedSession(
                    session_id=f"config_{config_name}",
                    title=f"OpenClaw Config: {config_name}",
                    project_path=None,
                    model=None,
                    status="completed",
                    started_at=None,
                    ended_at=None,
                    file_path=config_path,
                    file_size_bytes=stat.st_size,
                    file_mtime=stat.st_mtime,
                    raw_metadata={"source": "config"},
                )

    def parse_messages(self, session: ParsedSession) -> Generator[ParsedMessage, None, None]:
        """Parse OpenClaw session and knowledge files."""
        if not os.path.isfile(session.file_path):
            return

        if session.file_path.endswith(".md"):
            try:
                with open(session.file_path, "r", encoding="utf-8") as f:
                    content = f.read(10000)
                yield ParsedMessage(
                    message_id="full",
                    role="system",
                    content_text=self._truncate(content, 5000),
                    content_type="markdown",
                    seq=0,
                )
            except OSError:
                return
        elif session.file_path.endswith(".jsonl"):
            seq = 0
            for raw in self._safe_read_jsonl(session.file_path):
                text = raw.get("text", "") or raw.get("content", "") or json.dumps(raw)[:2000]
                if not text:
                    continue
                seq += 1
                yield ParsedMessage(
                    message_id=raw.get("id"),
                    role=raw.get("role", "system"),
                    content_text=self._truncate(text, 3000),
                    content_type="text",
                    timestamp=raw.get("timestamp"),
                    seq=seq,
                )
        elif session.file_path.endswith(".json"):
            try:
                with open(session.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                text = json.dumps(data, indent=2)[:5000]
                yield ParsedMessage(
                    message_id="full",
                    role="system",
                    content_text=self._truncate(text, 5000),
                    content_type="text",
                    seq=0,
                )
            except (json.JSONDecodeError, OSError):
                return

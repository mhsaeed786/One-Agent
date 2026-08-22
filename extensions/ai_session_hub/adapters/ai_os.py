"""AI-OS adapter — parses ~/.ai-os/ markdown and knowledge documents."""

import json
import os
from typing import Generator

from adapters.base import BaseAdapter, ParsedSession, ParsedMessage


class AiOsAdapter(BaseAdapter):
    TOOL_NAME = "ai_os"
    DISPLAY_NAME = "AI-OS"

    def discover_sessions(self) -> Generator[ParsedSession, None, None]:
        """Walk ~/.ai-os/ for markdown docs and session data."""
        if not os.path.isdir(self.data_path):
            return

        for root, _dirs, files in os.walk(self.data_path):
            for fname in files:
                fpath = os.path.join(root, fname)
                if not fname.endswith((".md", ".json", ".jsonl", ".txt")):
                    continue

                stat = os.stat(fpath)
                rel_path = os.path.relpath(fpath, self.data_path)

                # Generate a meaningful title
                title = f"AI-OS: {rel_path}"
                if fname.endswith(".md"):
                    # Try to read first line as title
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            first_line = f.readline().strip()
                        if first_line.startswith("#"):
                            title = first_line.lstrip("#").strip()
                    except OSError:
                        pass

                yield ParsedSession(
                    session_id=rel_path.replace(os.sep, "_").replace(".", "_"),
                    title=title,
                    project_path=os.path.dirname(rel_path) or None,
                    model=None,
                    status="completed",
                    started_at=None,
                    ended_at=None,
                    file_path=fpath,
                    file_size_bytes=stat.st_size,
                    file_mtime=stat.st_mtime,
                    raw_metadata={"rel_path": rel_path, "format": os.path.splitext(fname)[1]},
                )

    def parse_messages(self, session: ParsedSession) -> Generator[ParsedMessage, None, None]:
        """Parse AI-OS documents as single-message sessions."""
        if not os.path.isfile(session.file_path):
            return

        fmt = session.raw_metadata.get("format", "") if session.raw_metadata else ""

        if fmt == ".md" or session.file_path.endswith(".md"):
            try:
                with open(session.file_path, "r", encoding="utf-8") as f:
                    content = f.read(20000)
                yield ParsedMessage(
                    message_id="full",
                    role="system",
                    content_text=self._truncate(content, 10000),
                    content_type="markdown",
                    seq=0,
                )
            except OSError:
                return
        elif fmt == ".jsonl" or session.file_path.endswith(".jsonl"):
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
        elif fmt in (".json", ".txt") or session.file_path.endswith((".json", ".txt")):
            try:
                with open(session.file_path, "r", encoding="utf-8") as f:
                    content = f.read(10000)
                yield ParsedMessage(
                    message_id="full",
                    role="system",
                    content_text=self._truncate(content, 5000),
                    content_type="text",
                    seq=0,
                )
            except OSError:
                return

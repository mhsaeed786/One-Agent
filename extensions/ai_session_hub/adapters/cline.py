"""Cline adapter — parses ~/.cline/ workspace and history data."""

import json
import os
from typing import Generator

from adapters.base import BaseAdapter, ParsedSession, ParsedMessage


class ClineAdapter(BaseAdapter):
    TOOL_NAME = "cline"
    DISPLAY_NAME = "Cline"

    def discover_sessions(self) -> Generator[ParsedSession, None, None]:
        """Walk ~/.cline/ for task history and settings."""
        if not os.path.isdir(self.data_path):
            return

        # Check for task history in common Cline locations
        tasks_dir = os.path.join(self.data_path, "tasks")
        if os.path.isdir(tasks_dir):
            for fname in os.listdir(tasks_dir):
                fpath = os.path.join(tasks_dir, fname)
                if os.path.isfile(fpath) and fname.endswith(".json"):
                    stat = os.stat(fpath)
                    yield ParsedSession(
                        session_id=fname.replace(".json", ""),
                        title=f"Cline Task: {fname}",
                        project_path=None,
                        model=None,
                        status="completed",
                        started_at=None,
                        ended_at=None,
                        file_path=fpath,
                        file_size_bytes=stat.st_size,
                        file_mtime=stat.st_mtime,
                        raw_metadata={"source": "tasks"},
                    )

        # Check for global storage / state db (VS Code extension data)
        global_storage = os.path.join(self.data_path, "globalStorage")
        if os.path.isdir(global_storage):
            for fname in os.listdir(global_storage):
                fpath = os.path.join(global_storage, fname)
                if not os.path.isfile(fpath):
                    continue
                if fname.endswith(".json") or fname.endswith(".jsonl"):
                    stat = os.stat(fpath)
                    yield ParsedSession(
                        session_id=f"global_{fname}",
                        title=f"Cline State: {fname}",
                        project_path=None,
                        model=None,
                        status="completed",
                        started_at=None,
                        ended_at=None,
                        file_path=fpath,
                        file_size_bytes=stat.st_size,
                        file_mtime=stat.st_mtime,
                        raw_metadata={"source": "globalStorage"},
                    )

        # Check for cline_history in vscode extensions
        vscode_cline = os.path.expanduser(
            "~/.vscode/extensions/saoudrizwan.claude-dev-*"
        )
        if os.path.isdir(os.path.expanduser("~/.vscode/extensions")):
            import glob
            for ext_dir in glob.glob(
                os.path.expanduser("~/.vscode/extensions/saoudrizwan.claude-dev-*")
            ):
                # VS Code extension workspace storage is complex — just note it exists
                stat = os.stat(ext_dir)
                yield ParsedSession(
                    session_id=f"vscode_ext_{os.path.basename(ext_dir)}",
                    title=f"Cline VS Code Extension",
                    project_path=None,
                    model=None,
                    status="completed",
                    started_at=None,
                    ended_at=None,
                    file_path=ext_dir,
                    file_size_bytes=stat.st_size,
                    file_mtime=stat.st_mtime,
                    raw_metadata={"source": "vscode_extension", "path": ext_dir},
                )

    def parse_messages(self, session: ParsedSession) -> Generator[ParsedMessage, None, None]:
        """Parse Cline task/state files."""
        if not os.path.isfile(session.file_path):
            return

        if session.file_path.endswith(".jsonl"):
            seq = 0
            for raw in self._safe_read_jsonl(session.file_path):
                seq += 1
                text = raw.get("text", "") or raw.get("content", "") or json.dumps(raw)[:2000]
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

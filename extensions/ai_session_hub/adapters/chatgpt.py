"""ChatGPT adapter — parses ~/.chatgpt/ config and conversation data."""

import json
import os
from typing import Generator

from adapters.base import BaseAdapter, ParsedSession, ParsedMessage


class ChatGptAdapter(BaseAdapter):
    TOOL_NAME = "chatgpt"
    DISPLAY_NAME = "ChatGPT"

    def discover_sessions(self) -> Generator[ParsedSession, None, None]:
        """Walk ~/.chatgpt/ for conversation data."""
        if not os.path.isdir(self.data_path):
            return

        # Look for conversation export files
        for root, _dirs, files in os.walk(self.data_path):
            for fname in files:
                fpath = os.path.join(root, fname)
                stat = os.stat(fpath)

                if fname.endswith(".json"):
                    # Try to detect conversation format
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            data = json.load(f)

                        # ChatGPT export format: list of conversations
                        if isinstance(data, list):
                            for conv in data:
                                if isinstance(conv, dict) and conv.get("id"):
                                    yield ParsedSession(
                                        session_id=conv["id"],
                                        title=conv.get("title", f"ChatGPT: {conv['id'][:8]}"),
                                        project_path=None,
                                        model=conv.get("model"),
                                        status="completed",
                                        started_at=conv.get("create_time"),
                                        ended_at=conv.get("update_time"),
                                        file_path=fpath,
                                        file_size_bytes=stat.st_size,
                                        file_mtime=stat.st_mtime,
                                        raw_metadata=conv.get("metadata"),
                                    )
                        elif isinstance(data, dict):
                            # Single conversation
                            conv_id = data.get("id", fname.replace(".json", ""))
                            yield ParsedSession(
                                session_id=conv_id,
                                title=data.get("title", f"ChatGPT: {conv_id[:8]}"),
                                project_path=None,
                                model=data.get("model"),
                                status="completed",
                                started_at=data.get("create_time"),
                                ended_at=data.get("update_time"),
                                file_path=fpath,
                                file_size_bytes=stat.st_size,
                                file_mtime=stat.st_mtime,
                                raw_metadata=data.get("metadata"),
                            )
                    except (json.JSONDecodeError, OSError):
                        # Not a valid conversation file — index as raw text
                        yield ParsedSession(
                            session_id=fname,
                            title=f"ChatGPT File: {fname}",
                            project_path=None,
                            model=None,
                            status="completed",
                            started_at=None,
                            ended_at=None,
                            file_path=fpath,
                            file_size_bytes=stat.st_size,
                            file_mtime=stat.st_mtime,
                            raw_metadata={"source": "raw"},
                        )

                elif fname.endswith((".jsonl", ".md", ".txt")):
                    yield ParsedSession(
                        session_id=fname,
                        title=f"ChatGPT: {fname}",
                        project_path=None,
                        model=None,
                        status="completed",
                        started_at=None,
                        ended_at=None,
                        file_path=fpath,
                        file_size_bytes=stat.st_size,
                        file_mtime=stat.st_mtime,
                        raw_metadata={"source": "raw"},
                    )

    def parse_messages(self, session: ParsedSession) -> Generator[ParsedMessage, None, None]:
        """Parse ChatGPT conversation messages."""
        if not os.path.isfile(session.file_path):
            return

        if session.file_path.endswith(".json"):
            try:
                with open(session.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Extract conversation node tree
                conversations = data if isinstance(data, list) else [data]
                seq = 0

                for conv in conversations:
                    if not isinstance(conv, dict):
                        continue

                    # ChatGPT export: mapping of nodes
                    mapping = conv.get("mapping", {})
                    if mapping:
                        for node_id, node in mapping.items():
                            msg = node.get("message", {})
                            if not msg:
                                continue

                            role = msg.get("author", {}).get("role", "")
                            if role not in ("user", "assistant", "system", "tool"):
                                continue

                            parts = msg.get("content", {}).get("parts", [])
                            text = "\n".join(
                                str(p) for p in parts if isinstance(p, str)
                            )
                            if not text:
                                continue

                            seq += 1
                            yield ParsedMessage(
                                message_id=node_id,
                                role=role,
                                content_text=self._truncate(text, 5000),
                                content_type="text",
                                model=msg.get("metadata", {}).get("model_slug"),
                                timestamp=msg.get("create_time"),
                                seq=seq,
                            )
                    else:
                        # Simple format: direct messages array
                        messages = conv.get("messages", [])
                        for msg in messages:
                            role = msg.get("role", "system")
                            text = msg.get("content", "")
                            if not text:
                                continue
                            seq += 1
                            yield ParsedMessage(
                                message_id=msg.get("id"),
                                role=role if role in ("user", "assistant", "system") else "system",
                                content_text=self._truncate(str(text), 5000),
                                content_type="text",
                                timestamp=msg.get("timestamp"),
                                seq=seq,
                            )

            except (json.JSONDecodeError, OSError):
                return
        elif session.file_path.endswith(".jsonl"):
            seq = 0
            for raw in self._safe_read_jsonl(session.file_path):
                text = raw.get("text", "") or raw.get("content", "")
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

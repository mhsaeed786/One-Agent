"""Gemini Antigravity adapter — indexes .pb file metadata from ~/.gemini/antigravity/."""

import os
from datetime import datetime, timezone
from typing import Generator

from adapters.base import BaseAdapter, ParsedSession, ParsedMessage


class GeminiAntigravityAdapter(BaseAdapter):
    TOOL_NAME = "gemini_antigravity"
    DISPLAY_NAME = "Gemini Antigravity"

    def discover_sessions(self) -> Generator[ParsedSession, None, None]:
        """List .pb conversation files as sessions (content is encrypted/protobuf)."""
        conv_dir = os.path.join(self.data_path, "conversations")
        if not os.path.isdir(conv_dir):
            return

        for fname in os.listdir(conv_dir):
            if not fname.endswith(".pb"):
                continue
            fpath = os.path.join(conv_dir, fname)
            stat = os.stat(fpath)

            # Extract timestamp from modification time
            started = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()

            yield ParsedSession(
                session_id=fname.replace(".pb", ""),
                title=f"Antigravity Conversation ({fname[:16]}...)",
                project_path=None,
                model="gemini",
                status="completed",
                started_at=started,
                ended_at=None,
                file_path=fpath,
                file_size_bytes=stat.st_size,
                file_mtime=stat.st_mtime,
                raw_metadata={
                    "format": "protobuf",
                    "note": "Content encrypted/binary - not extractable without protobuf schema",
                },
            )

    def parse_messages(self, session: ParsedSession) -> Generator[ParsedMessage, None, None]:
        """No messages can be extracted from encrypted .pb files."""
        yield ParsedMessage(
            message_id="meta",
            role="system",
            content_text=f"Encrypted protobuf conversation file ({session.file_size_bytes} bytes). "
                         f"Content not extractable without Google's protobuf schema definition.",
            content_type="text",
            model="gemini",
            seq=0,
        )

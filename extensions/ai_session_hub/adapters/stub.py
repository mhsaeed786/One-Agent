"""Stub adapter — for tools with no discoverable session data."""

import os
from typing import Generator

from adapters.base import BaseAdapter, ParsedSession, ParsedMessage


class StubAdapter(BaseAdapter):
    """Placeholder adapter for tools with no usable session storage.

    Used for: Goose, Trae, Codeium, Windsurf, and other tools that
    either store sessions server-side only or have no local data.
    """

    TOOL_NAME = "stub"
    DISPLAY_NAME = "Unknown (Stub)"

    def discover_sessions(self) -> Generator[ParsedSession, None, None]:
        """Check if the data path exists and report its existence."""
        if not os.path.isdir(self.data_path):
            return

        # Check if there's any readable content at all
        total_size = 0
        file_count = 0
        for root, _dirs, files in os.walk(self.data_path):
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    total_size += os.path.getsize(fpath)
                    file_count += 1
                except OSError:
                    continue

        if file_count == 0:
            return

        yield ParsedSession(
            session_id="stub_directory",
            title=f"{self.DISPLAY_NAME} — {file_count} files ({total_size:,} bytes)",
            project_path=None,
            model=None,
            status="completed",
            started_at=None,
            ended_at=None,
            file_path=self.data_path,
            file_size_bytes=total_size,
            file_mtime=0.0,
            raw_metadata={
                "file_count": file_count,
                "total_size": total_size,
                "note": f"No structured session data found for {self.DISPLAY_NAME}. "
                        f"Tool may store sessions server-side or use an unsupported format.",
            },
        )

    def parse_messages(self, session: ParsedSession) -> Generator[ParsedMessage, None, None]:
        """Yield a single informational message."""
        yield ParsedMessage(
            message_id="stub_info",
            role="system",
            content_text=(
                f"No structured session data available for {self.DISPLAY_NAME}. "
                f"Directory contains {session.raw_metadata.get('file_count', '?')} files "
                f"({session.file_size_bytes:,} bytes). "
                f"Sessions may be stored server-side or in an unsupported format."
            ),
            content_type="text",
            seq=0,
        )

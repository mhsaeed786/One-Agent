"""Base adapter interface for all AI tool session parsers."""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Generator, Optional


@dataclass
class ParsedSession:
    """A discovered session from an AI tool."""
    session_id: str
    title: Optional[str] = None
    project_path: Optional[str] = None
    model: Optional[str] = None
    status: str = "completed"
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    file_path: str = ""
    file_size_bytes: int = 0
    file_mtime: float = 0.0
    raw_metadata: Optional[dict] = None


@dataclass
class ParsedMessage:
    """A single message within a session."""
    message_id: Optional[str] = None
    role: str = "user"
    content_text: Optional[str] = None
    content_type: str = "text"
    model: Optional[str] = None
    timestamp: Optional[str] = None
    token_input: Optional[int] = None
    token_output: Optional[int] = None
    raw_json: Optional[dict] = None
    parent_id: Optional[str] = None
    seq: int = 0


class BaseAdapter(ABC):
    """Abstract base class for AI tool session adapters.

    Each adapter knows how to discover session files for a specific AI tool
    and parse them into a normalized format.
    """

    TOOL_NAME: str = ""
    DISPLAY_NAME: str = ""

    def __init__(self, data_path: str = ""):
        self.data_path = data_path

    @abstractmethod
    def discover_sessions(self) -> Generator[ParsedSession, None, None]:
        """Walk the tool's data directory and yield session descriptors."""
        pass

    @abstractmethod
    def parse_messages(self, session: ParsedSession) -> Generator[ParsedMessage, None, None]:
        """Given a session descriptor, parse and yield its messages."""
        pass

    def is_available(self) -> bool:
        """Check if the tool's data directory exists."""
        return bool(self.data_path) and os.path.isdir(self.data_path)

    def _truncate(self, text: Optional[str], max_len: int = 500) -> Optional[str]:
        """Truncate text to max_len characters."""
        if not text:
            return text
        if len(text) <= max_len:
            return text
        return text[:max_len] + "..."

    def _safe_read_jsonl(self, path: str) -> Generator[dict, None, None]:
        """Read a JSONL file line-by-line, skipping bad lines."""
        import json
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue
        except (OSError, PermissionError):
            return

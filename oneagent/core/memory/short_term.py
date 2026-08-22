"""
Short-term Memory - Wraps ConversationBuffer from src/memory/buffer.py
"""

from typing import List, Dict, Any
from datetime import datetime


class ConversationBuffer:
    """Simple conversation memory buffer."""

    def __init__(self, max_messages: int = 100):
        self.max_messages = max_messages
        self.messages: List[Dict[str, Any]] = []

    def add(self, role: str, content: str, metadata: Dict = None) -> None:
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        })
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)

    def get_messages(self) -> List[Dict[str, Any]]:
        return self.messages.copy()

    def clear(self) -> None:
        self.messages.clear()

    def to_llm_format(self) -> List[Dict[str, str]]:
        return [{"role": m["role"], "content": m["content"]} for m in self.messages]


class ShortTermMemory:
    """
    Short-term memory for conversation context.
    Wraps ConversationBuffer for session-based memory.
    """

    def __init__(self, max_messages: int = 100):
        self.buffer = ConversationBuffer(max_messages)

    def add(self, role: str, content: str, metadata: Dict = None) -> None:
        self.buffer.add(role, content, metadata)

    def get_messages(self) -> List[Dict[str, Any]]:
        return self.buffer.get_messages()

    def clear(self) -> None:
        self.buffer.clear()

    def to_llm_format(self) -> List[Dict[str, str]]:
        return self.buffer.to_llm_format()

    def __len__(self) -> int:
        return len(self.buffer.messages)
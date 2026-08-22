"""Adapter registry — maps class names to adapter classes."""

from adapters.base import BaseAdapter
from adapters.claude_code import ClaudeCodeAdapter
from adapters.codex import CodexAdapter
from adapters.codex_sqlite import CodexSQLiteAdapter
from adapters.commandcode import CommandCodeAdapter
from adapters.gemini_cli import GeminiCliAdapter
from adapters.gemini_antigravity import GeminiAntigravityAdapter
from adapters.cursor import CursorAdapter
from adapters.cline import ClineAdapter
from adapters.openclaw import OpenClawAdapter
from adapters.ai_os import AiOsAdapter
from adapters.chatgpt import ChatGptAdapter
from adapters.hermes import HermesAdapter
from adapters.stub import StubAdapter

ADAPTER_REGISTRY = {
    "ClaudeCodeAdapter": ClaudeCodeAdapter,
    "CodexAdapter": CodexAdapter,
    "CodexSQLiteAdapter": CodexSQLiteAdapter,
    "CommandCodeAdapter": CommandCodeAdapter,
    "GeminiCliAdapter": GeminiCliAdapter,
    "GeminiAntigravityAdapter": GeminiAntigravityAdapter,
    "CursorAdapter": CursorAdapter,
    "ClineAdapter": ClineAdapter,
    "OpenClawAdapter": OpenClawAdapter,
    "AiOsAdapter": AiOsAdapter,
    "ChatGptAdapter": ChatGptAdapter,
    "HermesAdapter": HermesAdapter,
    "StubAdapter": StubAdapter,
}

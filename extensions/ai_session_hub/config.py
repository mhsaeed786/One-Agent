"""Central configuration for AI Session Hub."""

import os

HOME = os.path.expanduser("~")
# Derive BASE_DIR from this file's location so it works from any parent folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db", "session_hub.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "db", "schema.sql")

WEB_HOST = "127.0.0.1"
WEB_PORT = 5100

# --- Tool Data Paths ---
TOOL_CONFIGS = {
    "claude_code": {
        "display_name": "Claude Code",
        "adapter_class": "ClaudeCodeAdapter",
        "data_path": os.path.join(HOME, ".claude"),
        "enabled": True,
    },
    "codex": {
        "display_name": "Codex",
        "adapter_class": "CodexAdapter",
        "data_path": os.path.join(HOME, ".codex"),
        "enabled": True,
    },
    "codex_sqlite": {
        "display_name": "Codex (SQLite)",
        "adapter_class": "CodexSQLiteAdapter",
        "data_path": os.path.join(HOME, ".codex"),
        "enabled": True,
    },
    "commandcode": {
        "display_name": "CommandCode",
        "adapter_class": "CommandCodeAdapter",
        "data_path": os.path.join(HOME, ".commandcode"),
        "enabled": True,
    },
    "gemini_cli": {
        "display_name": "Gemini CLI",
        "adapter_class": "GeminiCliAdapter",
        "data_path": os.path.join(HOME, ".gemini", "antigravity-cli"),
        "enabled": True,
    },
    "gemini_antigravity": {
        "display_name": "Gemini Antigravity",
        "adapter_class": "GeminiAntigravityAdapter",
        "data_path": os.path.join(HOME, ".gemini", "antigravity"),
        "enabled": True,
    },
    "cursor": {
        "display_name": "Cursor",
        "adapter_class": "CursorAdapter",
        "data_path": os.path.join(HOME, ".cursor"),
        "enabled": True,
    },
    "cline": {
        "display_name": "Cline",
        "adapter_class": "ClineAdapter",
        "data_path": os.path.join(HOME, ".cline"),
        "enabled": True,
    },
    "openclaw": {
        "display_name": "OpenClaw",
        "adapter_class": "OpenClawAdapter",
        "data_path": os.path.join(HOME, ".openclaw"),
        "enabled": True,
    },
    "openclaw_wsl": {
        "display_name": "OpenClaw (WSL)",
        "adapter_class": "OpenClawAdapter",
        "data_path": "//wsl.localhost/Ubuntu/home/hassansaeed/.openclaw",
        "enabled": True,
    },
    "ai_os": {
        "display_name": "AI-OS",
        "adapter_class": "AiOsAdapter",
        "data_path": os.path.join(HOME, ".ai-os"),
        "enabled": True,
    },
    "chatgpt": {
        "display_name": "ChatGPT",
        "adapter_class": "ChatGptAdapter",
        "data_path": os.path.join(HOME, ".chatgpt"),
        "enabled": True,
    },
    "hermes": {
        "display_name": "Hermes (WSL)",
        "adapter_class": "HermesAdapter",
        "data_path": "//wsl.localhost/Ubuntu/home/hassansaeed/.hermes",
        "enabled": True,
    },
    "goose": {
        "display_name": "Goose",
        "adapter_class": "StubAdapter",
        "data_path": os.path.join(HOME, "AppData", "Roaming", "Goose"),
        "enabled": True,
    },
    "trae": {
        "display_name": "Trae",
        "adapter_class": "StubAdapter",
        "data_path": os.path.join(HOME, ".trae"),
        "enabled": True,
    },
    "codeium": {
        "display_name": "Codeium",
        "adapter_class": "StubAdapter",
        "data_path": os.path.join(HOME, ".codeium"),
        "enabled": True,
    },
    "windsurf": {
        "display_name": "Windsurf",
        "adapter_class": "StubAdapter",
        "data_path": os.path.join(HOME, "AppData", "Roaming", "Windsurf"),
        "enabled": True,
    },
}


def get_adapter(tool_name: str):
    """Instantiate and return the adapter for a tool."""
    from adapters import ADAPTER_REGISTRY

    cfg = TOOL_CONFIGS.get(tool_name)
    if not cfg:
        return None
    cls = ADAPTER_REGISTRY.get(cfg["adapter_class"])
    if not cls:
        return None
    return cls(data_path=cfg["data_path"])

"""
Agent Types - Enums and dataclasses for agent components
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
from datetime import datetime


class AgentState(Enum):
    """Agent execution states."""
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    WAITING = "waiting"
    DONE = "done"
    ERROR = "error"


@dataclass
class ToolResult:
    """Result from tool execution."""
    tool: str
    args: Dict[str, Any]
    success: bool
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0


@dataclass
class Step:
    """Single step in agent execution."""
    step_num: int
    thought: str
    action: Optional[str] = None
    action_args: Optional[Dict] = None
    observation: Optional[str] = None
    tool_result: Optional[ToolResult] = None


@dataclass
class AgentConfig:
    """Configuration for agent behavior."""
    name: str = "agent"
    model: str = "gpt-4"
    provider: str = "openai"
    max_iterations: int = 100
    max_retries: int = 3
    timeout: int = 300
    temperature: float = 0.7
    system_prompt: Optional[str] = None
    tools: List[str] = field(default_factory=list)
    memory_enabled: bool = True
    checkpoint_enabled: bool = True
"""
Data Models - SQLModel models for OneAgent
"""

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class UsageLog(SQLModel, table=True):
    """Token usage log entry."""
    __tablename__ = "usage_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    provider: str = ""
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    task_class: str = "default"
    cached: bool = False
    module: str = ""


class AgentRun(SQLModel, table=True):
    """Agent execution run record."""
    __tablename__ = "agent_runs"

    id: Optional[int] = Field(default=None, primary_key=True)
    agent_name: str = ""
    goal: str = ""
    started_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    success: bool = False
    iterations: int = 0
    total_cost_usd: float = 0.0
    error: Optional[str] = None
    module: str = ""


class ModuleManifest(SQLModel, table=True):
    """Module registration manifest."""
    __tablename__ = "module_manifests"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    enabled: bool = True
    route_prefix: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: Optional[str] = None
    config: str = "{}"  # JSON config blob

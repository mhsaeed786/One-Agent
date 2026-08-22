"""
OneAgent Settings - Single .env based configuration
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List
import os

from dotenv import load_dotenv


@dataclass
class LLMConfig:
    """LLM Provider configuration."""
    provider: str = "openai"
    model: str = "gpt-4"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 120


@dataclass
class ChromaConfig:
    """ChromaDB configuration."""
    host: str = "localhost"
    port: int = 8000
    collection_name: str = "oneagent_memory"
    embedding_provider: str = "openai"


@dataclass
class RedisConfig:
    """Redis configuration for distributed features."""
    host: str = "localhost"
    port: int = 6379
    password: str = ""
    db: int = 0


@dataclass
class BudgetConfig:
    """Budget configuration for cost tracking."""
    daily_limit_usd: float = 10.0
    monthly_limit_usd: float = 100.0
    warn_at_percent: float = 80.0


@dataclass
class OneAgentSettings:
    """Main configuration for OneAgent."""
    # General
    log_level: str = "INFO"
    log_dir: Path = field(default_factory=lambda: Path("./logs"))

    # LLM
    default_llm: LLMConfig = field(default_factory=LLMConfig)
    llm_fallback_order: List[str] = field(default_factory=lambda: ["openai", "anthropic", "ollama"])

    # Memory
    chroma: ChromaConfig = field(default_factory=ChromaConfig)
    memory_session_limit: int = 100

    # Cache
    cache_db_path: Path = field(default_factory=lambda: Path("./oneagent_cache.db"))
    cache_ttl_seconds: int = 3600

    # Budget
    budget: BudgetConfig = field(default_factory=BudgetConfig)

    # Redis (optional)
    redis: Optional[RedisConfig] = None

    # Paths
    workspace_dir: Path = field(default_factory=lambda: Path("./workspace"))

    @classmethod
    def from_env(cls, env_path: str = None) -> "OneAgentSettings":
        """Load settings from .env file."""
        load_dotenv(env_path)

        # Load API keys - support both ONEAGENT_* and provider-specific prefixes
        openai_key = os.getenv("OPENAI_API_KEY") or os.getenv("ONEAGENT_OPENAI_API_KEY")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ONEAGENT_ANTHROPIC_API_KEY")
        ollama_base = os.getenv("OLLAMA_BASE_URL") or os.getenv("ONEAGENT_OLLAMA_BASE_URL")

        return cls(
            log_level=os.getenv("ONEAGENT_LOG_LEVEL", "INFO"),
            default_llm=LLMConfig(
                provider=os.getenv("ONEAGENT_LLM_PROVIDER", "openai"),
                model=os.getenv("ONEAGENT_LLM_MODEL", "gpt-4"),
                api_key=openai_key,
                base_url=ollama_base,
            ),
            chroma=ChromaConfig(
                host=os.getenv("CHROMA_HOST", "localhost"),
                port=int(os.getenv("CHROMA_PORT", "8000")),
                collection_name=os.getenv("CHROMA_COLLECTION", "oneagent_memory"),
            ),
            redis=RedisConfig(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                password=os.getenv("REDIS_PASSWORD", ""),
            ) if os.getenv("REDIS_HOST") else None,
            budget=BudgetConfig(
                daily_limit_usd=float(os.getenv("ONEAGENT_DAILY_BUDGET", "10.0")),
                monthly_limit_usd=float(os.getenv("ONEAGENT_MONTHLY_BUDGET", "100.0")),
                warn_at_percent=float(os.getenv("ONEAGENT_WARN_AT_PERCENT", "80.0")),
            ),
            cache_db_path=Path(os.getenv("ONEAGENT_CACHE_DB", "./oneagent_cache.db")),
            cache_ttl_seconds=int(os.getenv("ONEAGENT_CACHE_TTL", "3600")),
        )
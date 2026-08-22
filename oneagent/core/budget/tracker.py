"""
Budget Tracker - Cost tracking and budget enforcement
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional
from collections import defaultdict
import threading

from ..llm.cache import SQLiteCache
from ..logging import get_logger

logger = get_logger("budget.tracker")


@dataclass
class UsageRecord:
    """Record of a single usage event."""
    timestamp: datetime
    cost_usd: float
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int


@dataclass
class BudgetStatus:
    """Current budget status."""
    daily_spent: float
    daily_limit: float
    monthly_spent: float
    monthly_limit: float
    can_spend: bool
    warning_active: bool


class BudgetTracker:
    """
    Track usage and enforce budget limits.

    Features:
    - Daily and monthly spending limits
    - Warning at configurable threshold (default 80%)
    - Per-provider and per-model breakdown
    - SQLite persistence for restart survival
    """

    def __init__(
        self,
        daily_limit: float = 10.0,
        monthly_limit: float = 100.0,
        warn_at_percent: float = 80.0,
        cache_db: Optional[SQLiteCache] = None,
    ):
        self.daily_limit = daily_limit
        self.monthly_limit = monthly_limit
        self.warn_at_percent = warn_at_percent

        self._cache = cache_db or SQLiteCache()
        self._lock = threading.RLock()  # Reentrant to avoid deadlock in get_status

        self._daily_spent = 0.0
        self._monthly_spent = 0.0
        self._usage_history: list = []

        self._load_state()

    def _load_state(self) -> None:
        """Load state from cache."""
        daily = self._cache.get("daily_spent")
        monthly = self._cache.get("monthly_spent")
        last_reset = self._cache.get("last_daily_reset")

        if last_reset:
            last_reset_dt = datetime.fromisoformat(last_reset)
            if datetime.now().date() > last_reset_dt.date():
                # New day, reset daily
                self._daily_spent = 0.0
                self._cache.set("daily_spent", 0.0)
                self._cache.set("last_daily_reset", datetime.now().isoformat())
            else:
                self._daily_spent = daily if daily else 0.0
        else:
            self._daily_spent = 0.0

        monthly_reset = self._cache.get("last_monthly_reset")
        if monthly_reset:
            monthly_reset_dt = datetime.fromisoformat(monthly_reset)
            if datetime.now().replace(day=1) > monthly_reset_dt.replace(day=1):
                # New month, reset monthly
                self._monthly_spent = 0.0
                self._cache.set("monthly_spent", 0.0)
                self._cache.set("last_monthly_reset", datetime.now().isoformat())
            else:
                self._monthly_spent = monthly if monthly else 0.0
        else:
            self._monthly_spent = 0.0

        self._usage_history = self._cache.get("usage_history") or []

    def _save_state(self) -> None:
        """Save state to cache."""
        self._cache.set("daily_spent", self._daily_spent, compute_hash=False)
        self._cache.set("monthly_spent", self._monthly_spent, compute_hash=False)
        self._cache.set("usage_history", self._usage_history, compute_hash=False)

    def can_spend(self, amount: float) -> bool:
        """Check if amount can be spent."""
        with self._lock:
            if self._daily_spent + amount > self.daily_limit:
                return False
            if self._monthly_spent + amount > self.monthly_limit:
                return False
            return True

    def record_usage(
        self,
        cost_usd: float,
        usage: Dict[str, int],
        provider: str = "unknown",
        model: str = "unknown",
    ) -> None:
        """Record a usage event."""
        with self._lock:
            record = UsageRecord(
                timestamp=datetime.now(),
                cost_usd=cost_usd,
                provider=provider,
                model=model,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
            )

            self._usage_history.append({
                "timestamp": record.timestamp.isoformat(),
                "cost_usd": record.cost_usd,
                "provider": record.provider,
                "model": record.model,
                "prompt_tokens": record.prompt_tokens,
                "completion_tokens": record.completion_tokens,
            })

            self._daily_spent += cost_usd
            self._monthly_spent += cost_usd

            self._save_state()

            # Check warning threshold
            daily_pct = (self._daily_spent / self.daily_limit) * 100
            monthly_pct = (self._monthly_spent / self.monthly_limit) * 100

            if daily_pct >= self.warn_at_percent or monthly_pct >= self.warn_at_percent:
                logger.warning(
                    f"Budget warning: Daily {daily_pct:.1f}%, Monthly {monthly_pct:.1f}%"
                )

    def get_status(self) -> BudgetStatus:
        """Get current budget status."""
        with self._lock:
            return BudgetStatus(
                daily_spent=self._daily_spent,
                daily_limit=self.daily_limit,
                monthly_spent=self._monthly_spent,
                monthly_limit=self.monthly_limit,
                can_spend=self.can_spend(0.01),  # Check if can spend minimum
                warning_active=(
                    (self._daily_spent / self.daily_limit) >= self.warn_at_percent or
                    (self._monthly_spent / self.monthly_limit) >= self.warn_at_percent
                ),
            )

    def get_usage_breakdown(self) -> Dict[str, Dict]:
        """Get usage breakdown by provider/model."""
        with self._lock:
            breakdown: Dict[str, Dict] = defaultdict(lambda: {"cost": 0.0, "requests": 0})

            for record_data in self._usage_history:
                key = f"{record_data['provider']}/{record_data['model']}"
                breakdown[key]["cost"] += record_data["cost_usd"]
                breakdown[key]["requests"] += 1

            return dict(breakdown)


class BudgetExceededError(Exception):
    """Raised when budget limit is exceeded."""
    pass
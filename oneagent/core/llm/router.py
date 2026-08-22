"""
Model Router - Ranking-based selection with user-editable ranking.yaml
"""

import yaml
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

from ..logging import get_logger

logger = get_logger("llm.router")


@dataclass
class ModelRanking:
    """Ranking configuration for a task class."""
    task_class: str
    models: List[str]  # In preference order (first = best)


class ModelRouter:
    """
    Routes LLM requests to the best model based on:
    1. User-editable ranking.yaml (task-class-specific)
    2. User override at various levels
    3. Default fallback order
    """

    DEFAULT_RANKING = {
        "classify": ["gpt-3.5-turbo", "claude-3-haiku", "gpt-4"],
        "extract": ["gpt-4", "claude-3-sonnet", "gpt-3.5-turbo"],
        "reason": ["gpt-4", "claude-3-sonnet", "gpt-3.5-turbo"],
        "code": ["gpt-4", "claude-3-sonnet", "gpt-3.5-turbo"],
        "long_context": ["gpt-4-32k", "claude-3-sonnet", "gpt-3.5-turbo-16k"],
        "vision": ["gpt-4-vision-preview", "claude-3-sonnet"],
        "default": ["gpt-4", "claude-3-sonnet", "gpt-3.5-turbo", "ollama/llama2"],
    }

    def __init__(self, fallback_order: List[str] = None):
        self.fallback_order = fallback_order or ["openai", "anthropic", "ollama"]
        self._rankings: Dict[str, ModelRanking] = {}
        self._ranking_file = Path("./ranking.yaml")
        self._load_ranking()

    def _load_ranking(self) -> None:
        """Load rankings from file if exists."""
        if self._ranking_file.exists():
            try:
                with open(self._ranking_file, 'r') as f:
                    data = yaml.safe_load(f) or {}
                    for task_class, models in data.items():
                        self._rankings[task_class] = ModelRanking(
                            task_class=task_class,
                            models=models
                        )
                logger.info(f"Loaded rankings from {self._ranking_file}")
            except Exception as e:
                logger.warning(f"Failed to load ranking.yaml: {e}")
                self._load_defaults()
        else:
            self._load_defaults()

    def _load_defaults(self) -> None:
        """Load default rankings."""
        for task_class, models in self.DEFAULT_RANKING.items():
            self._rankings[task_class] = ModelRanking(
                task_class=task_class,
                models=models
            )

    def get_models(self, task_class: str = "default", provider_hint: str = None) -> List[str]:
        """Get ordered list of models to try for a task class."""
        if task_class in self._rankings:
            return self._rankings[task_class].models
        return self._rankings["default"].models

    def get_providers(self, provider_hint: str = None) -> List[str]:
        """Get ordered list of providers to try."""
        if provider_hint:
            return [provider_hint] + [p for p in self.fallback_order if p != provider_hint]
        return self.fallback_order.copy()

    def save_ranking(self, task_class: str, models: List[str]) -> None:
        """Save a new ranking to file."""
        self._rankings[task_class] = ModelRanking(task_class=task_class, models=models)
        data = {tc: r.models for tc, r in self._rankings.items()}
        with open(self._ranking_file, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)
        logger.info(f"Saved ranking for {task_class} to {self._ranking_file}")
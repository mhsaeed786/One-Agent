from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ProviderConfig:
    name: str
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    fallback: Optional[str] = None  # provider:model format
    priority: int = 0
    supports_tools: bool = True
    supports_vision: bool = False


class ProviderFallbackRegistry:
    """Enhanced provider registry with automatic fallback support.

    Inspired by LiteLLM/Portkey patterns.
    """

    def __init__(self):
        self._providers: Dict[str, Any] = {}
        self._fallbacks: Dict[str, str] = {}
        self._priority: Dict[str, int] = {}

    def register(self, config: ProviderConfig):
        self._providers[config.name] = config
        self._priority[config.name] = config.priority
        if config.fallback:
            self._fallbacks[config.name] = config.fallback

    def resolve(self, name: str) -> ProviderConfig:
        if name in self._providers:
            return self._providers[name]
        raise ValueError(f"Unknown provider '{name}'. Registered: {list(self._providers)}")

    def get_fallback_chain(self, name: str) -> List[ProviderConfig]:
        chain = []
        current = name
        seen = set()
        while current and current not in seen:
            seen.add(current)
            if current in self._providers:
                chain.append(self._providers[current])
            current = self._fallbacks.get(current)
        return chain

    def list_providers(self) -> List[str]:
        return sorted(self._providers.keys(), key=lambda n: -self._priority.get(n, 0))


GLOBAL_FALLBACK_REGISTRY = ProviderFallbackRegistry()

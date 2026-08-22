"""
LLM Gateway - Unified gateway with caching, budget tracking, and failover
"""

import hashlib
import asyncio
from typing import Optional, Dict, Any, AsyncIterator

from dataclasses import dataclass

from .providers import AIProviderFactory, AIResponse
from .router import ModelRouter
from .cache import SQLiteCache
from ..budget.tracker import BudgetTracker, BudgetExceededError
from ..logging import get_logger

logger = get_logger("llm.gateway")


@dataclass
class LLMResponse:
    """Standardized LLM response for OneAgent."""
    content: str
    model: str
    provider: str
    usage: Dict[str, int]
    finish_reason: str
    latency_ms: float
    cost_usd: float
    cached: bool = False


class AllProvidersFailedError(Exception):
    """Raised when all LLM providers fail."""
    pass


class LLMGateway:
    """
    Unified LLM Gateway with:
    - Automatic failover between providers
    - Cost tracking per request
    - Token usage monitoring
    - Response caching
    - Budget enforcement
    """

    # Cost per 1M tokens (approximate)
    COST_MATRIX = {
        "openai/gpt-4": {"input": 30.0, "output": 60.0},
        "openai/gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
        "openai/gpt-4-32k": {"input": 60.0, "output": 120.0},
        "anthropic/claude-3-sonnet": {"input": 3.0, "output": 15.0},
        "anthropic/claude-3-haiku": {"input": 0.25, "output": 1.25},
        "ollama/llama2": {"input": 0.0, "output": 0.0},  # Local
    }

    def __init__(
        self,
        budget_tracker: BudgetTracker,
        cache_db: Optional[SQLiteCache] = None,
        fallback_order: list = None,
    ):
        self.budget_tracker = budget_tracker
        self.cache = cache_db or SQLiteCache()
        self.router = ModelRouter(fallback_order)
        self._event_loop = None

    def _get_cache_key(self, prompt: str, system_prompt: str = None, provider: str = None) -> str:
        """Generate cache key from prompt content."""
        content = f"{provider or 'default'}:{system_prompt or ''}:{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    async def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        provider_hint: str = None,
        task_class: str = "default",
        **kwargs
    ) -> LLMResponse:
        """
        Generate response with automatic failover and caching.
        """
        start_time = asyncio.get_event_loop().time()
        cache_key = self._get_cache_key(prompt, system_prompt, provider_hint)

        # Check cache first
        cached = self.cache.get(cache_key)
        if cached:
            logger.debug(f"Cache hit for key {cache_key}")
            return LLMResponse(
                content=cached["content"],
                model=cached["model"],
                provider=cached["provider"],
                usage=cached["usage"],
                finish_reason=cached.get("finish_reason", "stop"),
                latency_ms=0,
                cost_usd=0,
                cached=True
            )

        # Get providers to try
        providers_to_try = self.router.get_providers(provider_hint)

        # Estimate cost for budget check
        estimated_cost = self._estimate_cost(prompt, providers_to_try[0])
        if not self.budget_tracker.can_spend(estimated_cost):
            raise BudgetExceededError(f"Estimated cost {estimated_cost} exceeds remaining budget")

        last_error = None
        for provider_name in providers_to_try:
            try:
                provider = AIProviderFactory.create(provider_name)
                response = await provider.generate(prompt, system_prompt, **kwargs)

                # Calculate cost
                cost = self._calculate_cost(response.usage, provider_name, response.model)

                # Record usage
                self.budget_tracker.record_usage(cost, response.usage, provider_name, response.model)

                latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000

                result = LLMResponse(
                    content=response.content,
                    model=response.model,
                    provider=provider_name,
                    usage=response.usage,
                    finish_reason=response.finish_reason,
                    latency_ms=latency_ms,
                    cost_usd=cost,
                    cached=False
                )

                # Cache the response
                self.cache.set(cache_key, {
                    "content": response.content,
                    "model": response.model,
                    "provider": provider_name,
                    "usage": response.usage,
                    "finish_reason": response.finish_reason,
                })

                return result

            except Exception as e:
                last_error = e
                logger.warning(f"Provider {provider_name} failed: {e}")
                continue

        raise AllProvidersFailedError(f"All LLM providers failed. Last error: {last_error}")

    async def stream(
        self,
        prompt: str,
        system_prompt: str = None,
        provider_hint: str = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream response from LLM (no caching)."""
        provider_name = provider_hint or self.router.fallback_order[0]
        try:
            provider = AIProviderFactory.create(provider_name)
            async for chunk in provider.stream(prompt, system_prompt, **kwargs):
                yield chunk
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            raise

    def _estimate_cost(self, prompt: str, provider: str) -> float:
        """Estimate cost based on prompt length."""
        tokens = len(prompt) // 4  # Rough approximation
        cost_info = self.COST_MATRIX.get(provider, {"input": 1.0, "output": 2.0})
        return (tokens / 1_000_000) * cost_info["input"]

    def _calculate_cost(self, usage: Dict[str, int], provider: str, model: str) -> float:
        """Calculate actual cost from token usage."""
        key = f"{provider}/{model}"
        cost_info = self.COST_MATRIX.get(key, {"input": 1.0, "output": 2.0})

        input_tokens = usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0) or usage.get("output_tokens", 0)

        input_cost = (input_tokens / 1_000_000) * cost_info["input"]
        output_cost = (output_tokens / 1_000_000) * cost_info["output"]
        return input_cost + output_cost
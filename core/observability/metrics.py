from __future__ import annotations

from typing import Dict, List
from dataclasses import dataclass, field


@dataclass
class MetricEvent:
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    timestamp: str = ""


class CostTracker:
    """Track LLM costs across runs."""

    def __init__(self):
        self._events: List[MetricEvent] = []

    def record(self, event: MetricEvent):
        self._events.append(event)

    def total_cost(self) -> float:
        return sum(e.cost_usd for e in self._events)

    def by_provider(self) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for e in self._events:
            out[e.provider] = out.get(e.provider, 0.0) + e.cost_usd
        return out


class LatencyTracker:
    """Track LLM latency percentiles."""

    def __init__(self):
        self._latencies: List[float] = []

    def record(self, latency_ms: float):
        self._latencies.append(latency_ms)

    def p50(self) -> float:
        if not self._latencies:
            return 0.0
        s = sorted(self._latencies)
        return s[len(s) // 2]

    def p95(self) -> float:
        if not self._latencies:
            return 0.0
        s = sorted(self._latencies)
        return s[int(len(s) * 0.95)]

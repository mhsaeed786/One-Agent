from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum


class SpanKind(str, Enum):
    LLM = "llm"
    TOOL = "tool"
    AGENT = "agent"
    RETRIEVAL = "retrieval"


@dataclass
class Span:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None
    name: str = ""
    kind: SpanKind = SpanKind.AGENT
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0

    def finish(self):
        self.end_time = time.time()
        self.latency_ms = (self.end_time - self.start_time) * 1000


class ObservabilityTracer:
    """Lightweight tracing and observability for agent runs.

    Inspired by Langfuse/Helicone patterns.
    """

    def __init__(self):
        self._spans: List[Span] = []
        self._active: Optional[Span] = None
        self._callbacks: List[Callable] = []

    def on(self, callback: Callable[[Span], None]):
        self._callbacks.append(callback)

    def start_span(self, name: str, kind: SpanKind = SpanKind.AGENT, parent_id: Optional[str] = None) -> Span:
        span = Span(name=name, kind=kind, parent_id=parent_id)
        self._spans.append(span)
        self._active = span
        return span

    def end_span(self, span: Optional[Span] = None):
        target = span or self._active
        if target:
            target.finish()
            for cb in self._callbacks:
                try:
                    cb(target)
                except Exception:
                    pass
        self._active = None

    def get_spans(self) -> List[Span]:
        return list(self._spans)

    def get_trace_summary(self) -> Dict[str, Any]:
        total_latency = sum(s.latency_ms for s in self._spans)
        total_cost = sum(s.cost_usd for s in self._spans)
        total_input = sum(s.input_tokens for s in self._spans)
        total_output = sum(s.output_tokens for s in self._spans)
        return {
            "span_count": len(self._spans),
            "total_latency_ms": total_latency,
            "total_cost_usd": total_cost,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
        }


GLOBAL_TRACER = ObservabilityTracer()

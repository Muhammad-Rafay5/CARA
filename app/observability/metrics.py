"""
Metrics collector stub for CARA.
Tracks operational counters in-memory. Replace with Prometheus in production.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricsCollector:
    """
    In-memory metrics store.

    Thread-safety: Python's GIL protects simple int/float increments.
    For multi-process deployments, replace with Prometheus metrics.
    """

    _start_time: float = field(default_factory=time.monotonic)
    _total_requests: int = 0
    _successful_requests: int = 0
    _failed_requests: int = 0
    _total_tokens: int = 0
    _total_cost_usd: float = 0.0
    _total_model_calls: int = 0
    _total_tool_calls: int = 0
    _verification_scores: list[float] = field(default_factory=list)

    def record_request(self, *, success: bool) -> None:
        self._total_requests += 1
        if success:
            self._successful_requests += 1
        else:
            self._failed_requests += 1

    def record_tokens(self, count: int) -> None:
        self._total_tokens += count

    def record_cost(self, usd: float) -> None:
        self._total_cost_usd += usd

    def record_model_call(self, *args: Any, **kwargs: Any) -> None:
        self._total_model_calls += 1

    def record_tool_call(self, *args: Any, **kwargs: Any) -> None:
        self._total_tool_calls += 1

    def record_verification_score(self, score: float) -> None:
        self._verification_scores.append(score)

    @property
    def uptime_seconds(self) -> float:
        return time.monotonic() - self._start_time

    @property
    def average_verification_score(self) -> float:
        if not self._verification_scores:
            return 0.0
        return sum(self._verification_scores) / len(self._verification_scores)

    def snapshot(self) -> dict[str, Any]:
        """Return a point-in-time metrics snapshot."""
        return {
            "total_requests": self._total_requests,
            "successful_requests": self._successful_requests,
            "failed_requests": self._failed_requests,
            "total_tokens_used": self._total_tokens,
            "total_cost_usd": round(self._total_cost_usd, 6),
            "total_model_calls": self._total_model_calls,
            "total_tool_calls": self._total_tool_calls,
            "average_verification_score": round(self.average_verification_score, 4),
            "uptime_seconds": round(self.uptime_seconds, 2),
        }


# Application-lifetime singleton
metrics = MetricsCollector()

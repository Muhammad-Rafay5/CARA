"""
Model Usage and Latency Tracker for CARA.

Tracks token counts, request durations, and financial costs per provider/model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import time

from app.core.interfaces.model import ModelResponse
from app.observability.logging import get_logger
from app.observability.metrics import metrics

logger = get_logger(__name__)


@dataclass
class ModelUsageRecord:
    provider: str
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    duration_ms: float
    cost_usd: float
    timestamp: float = field(default_factory=time.time)


class UsageTracker:
    """
    In-memory tracker for model execution metrics and cumulative token/cost totals.
    """

    def __init__(self):
        self._records: List[ModelUsageRecord] = []
        self._totals_by_provider: Dict[str, Dict[str, float]] = {}

    def record_usage(
        self,
        response: ModelResponse,
        cost_usd: float = 0.0,
    ) -> ModelUsageRecord:
        """
        Record a model invocation result.
        """
        rec = ModelUsageRecord(
            provider=response.provider,
            model_name=response.model_name,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            total_tokens=response.total_tokens,
            duration_ms=response.duration_ms,
            cost_usd=cost_usd,
        )
        self._records.append(rec)

        # Update per-provider aggregates
        p = response.provider
        if p not in self._totals_by_provider:
            self._totals_by_provider[p] = {
                "calls": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_usd": 0.0,
            }
        self._totals_by_provider[p]["calls"] += 1
        self._totals_by_provider[p]["prompt_tokens"] += response.prompt_tokens
        self._totals_by_provider[p]["completion_tokens"] += response.completion_tokens
        self._totals_by_provider[p]["total_tokens"] += response.total_tokens
        self._totals_by_provider[p]["cost_usd"] += cost_usd

        # Also emit to global metrics collector
        metrics.record_model_call(
            provider=response.provider,
            tokens=response.total_tokens,
            duration_ms=response.duration_ms,
            cost_usd=cost_usd,
        )

        return rec

    def get_provider_totals(self, provider: str) -> Dict[str, float]:
        return self._totals_by_provider.get(
            provider,
            {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "cost_usd": 0.0},
        )

    def get_all_records(self) -> List[ModelUsageRecord]:
        return list(self._records)


usage_tracker = UsageTracker()

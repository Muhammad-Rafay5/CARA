"""
Metrics routes for CARA.
GET /api/v1/metrics — operational usage snapshot
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_metrics
from app.observability.metrics import MetricsCollector
from app.schemas.models import APIResponse, UsageMetrics

router = APIRouter(prefix="/api/v1", tags=["Metrics"])


@router.get(
    "/metrics",
    response_model=APIResponse[UsageMetrics],
    summary="Operational metrics snapshot",
    description="Returns aggregate token usage, cost, and request counters.",
)
async def get_usage_metrics(
    m: MetricsCollector = Depends(get_metrics),
) -> APIResponse[UsageMetrics]:
    """Current in-process metrics snapshot."""
    snapshot = m.snapshot()
    data = UsageMetrics(**snapshot)
    return APIResponse(success=True, data=data, message="Metrics retrieved.")

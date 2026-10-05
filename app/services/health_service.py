"""
Health Service for CARA.

Evaluates system dependencies, provider readiness, and operational status.
"""

from __future__ import annotations

from typing import Dict
from app.config.settings import settings
from app.models.registry import registry as model_registry
from app.observability.metrics import metrics


class HealthService:
    """
    Checks liveness, readiness, and subsystem statistics.
    """

    def get_liveness(self) -> Dict[str, str]:
        return {"status": "ok", "service": "cara"}

    def get_readiness(self) -> Dict[str, any]:
        available_models = len(model_registry.available())
        total_models = len(model_registry.all())

        return {
            "status": "ready" if available_models > 0 else "degraded",
            "available_models": available_models,
            "total_models": total_models,
            "uptime_seconds": round(metrics.uptime_seconds, 1),
            "environment": settings.ENVIRONMENT,
        }


health_service = HealthService()

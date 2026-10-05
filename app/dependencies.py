"""
Dependency injection container for CARA.
FastAPI dependency functions providing singleton access to shared services.
"""

from __future__ import annotations

from functools import lru_cache

from app.config.settings import AppSettings, settings
from app.observability.metrics import MetricsCollector, metrics


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """
    Provide the application settings singleton.

    Usage:
        @router.get("/")
        async def endpoint(cfg: AppSettings = Depends(get_settings)):
            ...
    """
    return settings


def get_metrics() -> MetricsCollector:
    """
    Provide the in-process metrics collector.

    Usage:
        @router.get("/metrics")
        async def endpoint(m: MetricsCollector = Depends(get_metrics)):
            ...
    """
    return metrics

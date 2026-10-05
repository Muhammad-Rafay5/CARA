"""
Health check routes for CARA.
GET /health  — basic liveness probe
GET /ready   — readiness probe (checks provider availability)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config.settings import AppSettings
from app.dependencies import get_settings
from app.schemas.models import HealthStatus

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthStatus,
    summary="Liveness probe",
    description="Returns 200 when the application process is running.",
)
async def liveness() -> HealthStatus:
    """Basic liveness check — no dependency validation."""
    return HealthStatus(status="healthy")


@router.get(
    "/ready",
    response_model=HealthStatus,
    summary="Readiness probe",
    description="Returns 200 when the application is ready to serve requests.",
)
async def readiness(cfg: AppSettings = Depends(get_settings)) -> HealthStatus:
    """
    Readiness check verifying configuration is loaded.
    Provider pings will be added in Phase 2.3.
    """
    providers_configured = {
        "groq": bool(cfg.GROQ_API_KEY),
        "gemini": bool(cfg.GEMINI_API_KEY),
        "openrouter": bool(cfg.OPENROUTER_API_KEY),
        "ollama": True,  # always available (local)
    }

    any_provider_ready = any(providers_configured.values())
    status = "healthy" if any_provider_ready else "degraded"

    return HealthStatus(
        status=status,
        providers=providers_configured,
        details={
            "environment": cfg.ENVIRONMENT,
            "max_iterations": cfg.MAX_RESEARCH_ITERATIONS,
            "max_tokens": cfg.MAX_TOKENS,
        },
    )

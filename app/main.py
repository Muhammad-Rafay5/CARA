"""
CARA — Cost-Aware Autonomous Research & Report Agent
FastAPI application entry point.

Startup sequence:
1. Configure structured logging
2. Register middleware (request ID, CORS)
3. Register global error handler
4. Include API routers
5. Expose lifespan events for startup/shutdown hooks
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.middleware.error_handler import global_error_handler
from app.api.middleware.rate_limiter import RateLimitMiddleware
from app.api.middleware.request_id import RequestIDMiddleware
from app.api.middleware.session import SessionMiddleware
from app.api.routes.health import router as health_router
from app.api.routes.metrics import router as metrics_router
from app.api.routes.research import router as research_router
from app.config.settings import settings
from app.observability.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan — runs setup on startup, teardown on shutdown."""
    # ── Startup ──────────────────────────────────────────────────────────────
    configure_logging(settings.LOG_LEVEL)
    logger.info(
        "cara_starting",
        environment=settings.ENVIRONMENT,
        host=settings.HOST,
        port=settings.PORT,
        max_iterations=settings.MAX_RESEARCH_ITERATIONS,
        max_tokens=settings.MAX_TOKENS,
        rate_limit=f"{settings.RATE_LIMIT_MAX_REQUESTS} req / {settings.RATE_LIMIT_WINDOW_SECONDS}s",
        session_ttl_hours=settings.SESSION_TOKEN_TTL_HOURS,
    )

    yield  # Application runs here

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("cara_shutting_down")


def create_app() -> FastAPI:
    """
    Application factory — creates and fully configures the FastAPI app.

    Using a factory pattern (instead of a module-level app instance) makes
    the app testable and avoids import-time side effects.
    """
    app = FastAPI(
        title="CARA — Cost-Aware Autonomous Research & Report Agent",
        description=(
            "A production-grade autonomous research agent with dynamic model "
            "selection, two-stage verification, targeted recovery, and strict "
            "cost/token budget guardrails."
        ),
        version="0.1.0",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url="/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
    )

    # ── Middleware (order matters — outermost = first to process request) ────
    # 1. Request ID — must be first so all downstream middleware can log it
    app.add_middleware(RequestIDMiddleware)

    # 2. Session — assigns a signed session token to every request
    app.add_middleware(SessionMiddleware)

    # 3. Rate Limiter — per-session sliding-window throttle
    app.add_middleware(RateLimitMiddleware)

    # 4. CORS — restrict origins in production
    allowed_origins = (
        ["*"] if settings.is_development else ["https://your-production-domain.com"]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Session-Token",
                        "X-RateLimit-Limit", "X-RateLimit-Remaining",
                        "X-RateLimit-Reset"],
    )

    # ── Global exception handler ─────────────────────────────────────────────
    app.add_exception_handler(Exception, global_error_handler)

    # ── Routers ──────────────────────────────────────────────────────────────
    app.include_router(health_router)
    app.include_router(research_router)
    app.include_router(metrics_router)

    return app


# WSGI/ASGI entry point
app = create_app()

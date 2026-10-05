"""Routes package for CARA."""

from app.api.routes.health import router as health_router
from app.api.routes.metrics import router as metrics_router
from app.api.routes.research import router as research_router

__all__ = ["health_router", "metrics_router", "research_router"]

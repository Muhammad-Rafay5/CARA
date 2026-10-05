"""
Finalize Graph Node for CARA.

Caches successful research reports, marks task completed, and updates metrics.
"""

from __future__ import annotations

from datetime import datetime, timezone
from app.observability.logging import get_logger
from app.observability.metrics import metrics
from app.optimization.cache import research_cache
from app.schemas.research import ResearchState, ResearchStatus

logger = get_logger(__name__)


async def finalize(state: ResearchState) -> ResearchState:
    """Complete workflow, record metrics, and cache output."""
    state.completed_at = datetime.now(timezone.utc)
    state.status = ResearchStatus.COMPLETED

    # Cache report
    if state.report and state.summary:
        research_cache.set(state.query, {
            "report": state.report,
            "summary": state.summary,
            "score": state.verification_score,
        })

    # Record operational metrics
    metrics.record_request(success=True)
    if state.verification_score is not None:
        metrics.record_verification_score(state.verification_score)

    logger.info(
        "Research workflow completed successfully",
        request_id=state.request_id,
        iterations=state.iteration,
        tool_calls=state.tool_calls,
        verification_score=state.verification_score,
    )

    return state

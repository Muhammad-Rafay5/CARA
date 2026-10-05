"""
Check Budget Graph Node for CARA.

Verifies execution counters (iterations, model calls, tool calls, tokens)
against strict hard boundaries.
"""

from __future__ import annotations

from app.observability.logging import get_logger
from app.optimization.budget_manager import budget_manager
from app.schemas.research import ResearchState, ResearchStatus

logger = get_logger(__name__)


async def check_budget(state: ResearchState) -> ResearchState:
    """Evaluate budget status; set warnings or flag state if exceeded."""
    is_ok, reason = budget_manager.check_budget(state)
    if not is_ok:
        logger.warning("Budget check flagged limit", reason=reason)
        state.warnings.append(reason)
        # If hard limit breached, transition status
        if state.iteration >= state.max_iterations or state.tokens_used >= state.max_tokens:
            state.status = ResearchStatus.BUDGET_EXCEEDED

    return state

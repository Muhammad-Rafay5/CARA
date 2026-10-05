"""
Recover Graph Node for CARA.

Applies targeted recovery strategy (query reformulation, provider fallback)
and increments iteration counter without blowing away valid gathered evidence.
"""

from __future__ import annotations

from app.observability.logging import get_logger
from app.recovery.manager import RecoveryManager
from app.recovery.recovery_strategy import RecoveryAction
from app.schemas.research import ResearchState

logger = get_logger(__name__)
recovery_manager = RecoveryManager()


async def recover(state: ResearchState) -> ResearchState:
    """Execute targeted recovery action to patch gaps."""
    state.iteration += 1

    # Reformulate query or add targeted search step to plan
    unsupported = state.unsupported_claims[0] if state.unsupported_claims else None
    new_query = recovery_manager.get_reformulated_query(state.query, unsupported)

    state.research_plan.append(f"Targeted search: '{new_query}'")
    logger.info(
        "Applied targeted recovery",
        iteration=state.iteration,
        new_step=new_query,
    )

    return state

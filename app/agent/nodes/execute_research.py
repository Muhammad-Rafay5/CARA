"""
Execute Research Graph Node for CARA.

Coordinates tool calls (search, scraping, document reading) for the active research step.
"""

from __future__ import annotations

from app.observability.logging import get_logger
from app.research.researcher import Researcher
from app.schemas.research import ResearchState

logger = get_logger(__name__)
researcher = Researcher()


async def execute_research(state: ResearchState) -> ResearchState:
    """Execute tools for the current plan step."""
    if state.current_step >= len(state.research_plan):
        logger.info("All plan steps executed", steps=len(state.research_plan))
        return state

    step_desc = state.research_plan[state.current_step]
    logger.info("Executing plan step", step=step_desc, step_index=state.current_step)

    new_evidence = await researcher.execute_step(state.query, step_desc, state)

    # Convert Evidence objects to dictionaries for state persistence
    for ev in new_evidence:
        state.evidence_items.append(ev.model_dump())

    state.current_step += 1
    return state

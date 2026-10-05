"""
Create Plan Graph Node for CARA.

Generates the ordered research steps based on query complexity.
"""

from __future__ import annotations

from app.observability.logging import get_logger
from app.research.planner import ResearchPlanner
from app.schemas.research import ResearchComplexity, ResearchState

logger = get_logger(__name__)
planner = ResearchPlanner()


async def create_plan(state: ResearchState) -> ResearchState:
    """Formulate the sequential research steps."""
    complexity = state.complexity or ResearchComplexity.MEDIUM
    plan = planner.create_plan(state.query, complexity)
    state.research_plan = plan
    state.current_step = 0

    logger.info("Research plan created", steps_count=len(plan), complexity=complexity.value)
    return state

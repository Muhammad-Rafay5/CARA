"""
Task Analysis Graph Node for CARA.

Determines query complexity, initializes research state parameters,
and checks for early cache hits.
"""

from __future__ import annotations

from app.observability.logging import get_logger
from app.optimization.cache import research_cache
from app.research.planner import ResearchPlanner
from app.schemas.research import ResearchState, ResearchStatus

logger = get_logger(__name__)
planner = ResearchPlanner()


async def analyze_task(state: ResearchState) -> ResearchState:
    """Analyze query complexity and check research cache."""
    logger.info("Starting task analysis", query=state.query[:60], depth=state.depth.value)

    # Check cache for existing completed report
    cached_report = research_cache.get(state.query)
    if cached_report:
        logger.info("Found cached research report for query", query=state.query[:40])
        state.report = cached_report.get("report")
        state.summary = cached_report.get("summary")
        state.status = ResearchStatus.COMPLETED
        return state

    # Analyze complexity
    complexity = planner.analyze_complexity(state.query, state.depth)
    state.complexity = complexity
    state.status = ResearchStatus.RUNNING

    logger.info("Task complexity analyzed", complexity=complexity.value)
    return state

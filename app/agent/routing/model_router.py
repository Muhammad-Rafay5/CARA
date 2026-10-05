"""
Model Router for CARA graph edges.

Evaluates whether early termination is triggered (e.g. cache hit) or continues to model selection.
"""

from app.schemas.research import ResearchState, ResearchStatus


def route_model(state: ResearchState) -> str:
    """Route after task analysis."""
    if state.status == ResearchStatus.COMPLETED:
        # Cache hit in analyze_task
        return "finalize"
    return "select_model"

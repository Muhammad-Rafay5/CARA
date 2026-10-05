"""
Research Router for CARA graph edges.

Determines whether research should continue executing plan steps or proceed to evidence collection.
"""

from app.schemas.research import ResearchState


def route_research(state: ResearchState) -> str:
    """Decide next step during research iteration."""
    if state.current_step < len(state.research_plan) and state.tool_calls < state.max_tool_calls:
        return "execute_research"
    return "collect_evidence"

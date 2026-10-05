"""
Recovery Router for CARA graph edges.

Directs next action after recovery strategy application.
"""

from app.schemas.research import ResearchState


def route_recovery(state: ResearchState) -> str:
    """Route after applying recovery patch."""
    if state.iteration < state.max_iterations and state.tool_calls < state.max_tool_calls:
        # Re-execute newly formulated search step
        return "execute_research"
    return "generate_report"

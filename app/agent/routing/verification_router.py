"""
Verification Router for CARA graph edges.

Routes based on Stage 1 verification outcome:
- PASS: Proceed directly to report generation.
- RESEARCH_MORE: Route to classify failure and targeted recovery.
- REVISE / ESCALATE: If iterations remaining, attempt recovery; otherwise synthesize best report.
"""

from app.schemas.research import ResearchState
from app.schemas.verification import VerificationDecision


def route_verification(state: ResearchState) -> str:
    """Route after Stage 1 verification."""
    status = state.verification_status

    if status == VerificationDecision.PASS.value:
        return "generate_report"

    # If within iteration limits, attempt recovery
    if state.iteration < state.max_iterations and state.tool_calls < state.max_tool_calls:
        return "classify_failure"

    # Boundaries reached, synthesize best report available
    return "generate_report"

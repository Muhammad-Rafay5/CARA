"""
Verify Research Graph Node for CARA.

Executes Stage 1 Verification on gathered evidence items, producing a
formal decision: PASS, RESEARCH_MORE, REVISE, or ESCALATE.
"""

from __future__ import annotations

from app.observability.logging import get_logger
from app.schemas.evidence import Evidence
from app.schemas.research import ResearchState
from app.verification.verifier import Verifier

logger = get_logger(__name__)
verifier = Verifier()


async def verify_research(state: ResearchState) -> ResearchState:
    """Run Stage 1 evidence verification pass."""
    evidence_objs = [Evidence(**item) for item in state.evidence_items]

    v_result = verifier.verify_evidence(
        query=state.query,
        evidence_list=evidence_objs,
        iteration=state.iteration,
        max_iterations=state.max_iterations,
    )

    state.verification_score = v_result.score
    state.verification_status = v_result.decision.value
    state.unsupported_claims = v_result.unsupported_claims

    logger.info(
        "Stage 1 research verification evaluated",
        decision=v_result.decision.value,
        score=v_result.score,
        iteration=state.iteration,
    )

    return state

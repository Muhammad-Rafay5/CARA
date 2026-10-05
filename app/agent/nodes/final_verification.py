"""
Final Verification Graph Node for CARA.

Executes Stage 2 verification auditing final report citations and factual grounding.
"""

from __future__ import annotations

from app.observability.logging import get_logger
from app.schemas.evidence import Evidence
from app.schemas.report import Report, ReportSection
from app.schemas.research import ResearchState
from app.verification.verifier import Verifier

logger = get_logger(__name__)
verifier = Verifier()


async def final_verification(state: ResearchState) -> ResearchState:
    """Run Stage 2 report verification pass."""
    evidence_objs = [Evidence(**item) for item in state.evidence_items]

    # Reconstruct report object for audit
    dummy_report = Report(
        title=f"Report: {state.query}",
        summary=state.summary or "Summary of findings",
        sections=[ReportSection(heading="Findings", content=state.report or "")],
        citations=[],
        verification_score=state.verification_score or 0.85,
    )

    v_result = verifier.verify_report(dummy_report, evidence_objs)
    state.verification_score = v_result.score
    logger.info("Stage 2 report audit completed", score=v_result.score, risk=v_result.hallucination_risk)
    return state

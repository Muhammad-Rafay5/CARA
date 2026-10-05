"""
Verification Result Factory for CARA.

Constructs structured VerificationResult instances based on calculated quality metrics
and verification decisions.
"""

from __future__ import annotations

from typing import List, Optional

from app.schemas.verification import ClaimVerdict, VerificationDecision, VerificationResult


def build_verification_result(
    stage: int,
    decision: VerificationDecision,
    score: float,
    claim_verdicts: Optional[List[ClaimVerdict]] = None,
    unsupported_claims: Optional[List[str]] = None,
    missing_info: Optional[List[str]] = None,
    contradictions_found: Optional[List[str]] = None,
    hallucination_risk: float = 0.0,
    rationale: str = "",
) -> VerificationResult:
    """
    Build a strictly validated VerificationResult model.
    """
    return VerificationResult(
        stage=stage,
        decision=decision,
        score=score,
        claim_verdicts=claim_verdicts or [],
        unsupported_claims=unsupported_claims or [],
        missing_info=missing_info or [],
        contradictions_found=contradictions_found or [],
        hallucination_risk=hallucination_risk,
        rationale=rationale,
    )

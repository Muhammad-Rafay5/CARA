"""
Verification schemas for CARA.
Two-stage verification result models (evidence stage + final report stage).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class VerificationDecision(str, Enum):
    PASS = "PASS"                     # Quality threshold met → proceed
    RESEARCH_MORE = "RESEARCH_MORE"   # Insufficient evidence → iterate
    REVISE = "REVISE"                 # Claims need targeted repair
    ESCALATE = "ESCALATE"             # Cannot recover → partial result


class ClaimVerdict(BaseModel):
    """Verdict for a single claim extracted from the report."""

    claim: str
    supported: bool
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_urls: list[str] = Field(default_factory=list)
    contradicting_urls: list[str] = Field(default_factory=list)
    notes: str = ""


class VerificationResult(BaseModel):
    """
    Structured output from a verification pass (Stage 1 or Stage 2).

    Stage 1: Verifies gathered evidence completeness and quality.
    Stage 2: Verifies final report claims against all evidence.
    """

    stage: int = Field(..., ge=1, le=2, description="Verification stage (1 or 2).")
    decision: VerificationDecision
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Aggregate quality score (0.0 – 1.0).",
    )
    claim_verdicts: list[ClaimVerdict] = Field(
        default_factory=list,
        description="Per-claim verification results.",
    )
    unsupported_claims: list[str] = Field(
        default_factory=list,
        description="Claims that lack sufficient evidence support.",
    )
    missing_info: list[str] = Field(
        default_factory=list,
        description="Identified knowledge gaps that need additional research.",
    )
    contradictions_found: list[str] = Field(
        default_factory=list,
        description="Detected contradictions between sources.",
    )
    hallucination_risk: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Estimated probability of hallucinated content (0.0 – 1.0).",
    )
    rationale: str = Field(
        default="",
        description="Human-readable summary of verification reasoning.",
    )

    @property
    def passed(self) -> bool:
        """True only when PASS decision is reached."""
        return self.decision == VerificationDecision.PASS

    @property
    def needs_more_research(self) -> bool:
        return self.decision == VerificationDecision.RESEARCH_MORE

    @property
    def needs_revision(self) -> bool:
        return self.decision == VerificationDecision.REVISE

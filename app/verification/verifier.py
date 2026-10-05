"""
Two-Stage Verification Engine for CARA.

Stage 1: Evidence Verification
    - Assesses completeness, credibility, and contradictions of gathered evidence.
    - Decides: PASS (score >= 0.75), RESEARCH_MORE (iteration < max), REVISE, or ESCALATE.

Stage 2: Report Verification
    - Audits generated report against raw evidence and citations.
    - Checks citation validity, unsupported assertions, and hallucination probability.
"""

from __future__ import annotations

from typing import List, Optional

from app.core.constants import VERIFICATION_PASS_THRESHOLD
from app.observability.logging import get_logger
from app.observability.metrics import metrics
from app.research.contradiction import ContradictionDetector
from app.schemas.evidence import Evidence
from app.schemas.report import Report
from app.schemas.verification import ClaimVerdict, VerificationDecision, VerificationResult
from app.verification.claim_checker import ClaimChecker
from app.verification.quality_score import calculate_quality_score
from app.verification.source_checker import SourceChecker
from app.verification.verification_result import build_verification_result

logger = get_logger(__name__)


class Verifier:
    """
    Two-stage research verifier implementing strict verification thresholds.
    """

    def __init__(
        self,
        claim_checker: Optional[ClaimChecker] = None,
        source_checker: Optional[SourceChecker] = None,
        contradiction_detector: Optional[ContradictionDetector] = None,
        pass_threshold: float = VERIFICATION_PASS_THRESHOLD,
    ):
        self.claim_checker = claim_checker or ClaimChecker()
        self.source_checker = source_checker or SourceChecker()
        self.contradiction_detector = contradiction_detector or ContradictionDetector()
        self.pass_threshold = pass_threshold

    def verify_evidence(
        self,
        query: str,
        evidence_list: List[Evidence],
        iteration: int = 1,
        max_iterations: int = 3,
        min_evidence_count: int = 3,
    ) -> VerificationResult:
        """
        Stage 1: Verify gathered evidence sufficiency before report synthesis.
        """
        # 1. Detect conflicts
        conflicts = self.contradiction_detector.detect_conflicts(evidence_list)
        conflict_descs = [c.discrepancy_description for c in conflicts]

        # 2. Check sources
        source_analysis = self.source_checker.check_sources(evidence_list)

        # 3. Check claims in evidence
        claims = [e.claim for e in evidence_list]
        verdicts = self.claim_checker.check_claims(claims, evidence_list)

        # 4. Calculate quality score
        score = calculate_quality_score(
            claim_verdicts=verdicts,
            evidence_list=evidence_list,
            contradictions_count=len(conflicts),
            min_evidence_target=min_evidence_count,
        )

        unsupported = [v.claim for v in verdicts if not v.supported]

        # 5. Determine decision
        if len(evidence_list) < min_evidence_count:
            if iteration < max_iterations:
                decision = VerificationDecision.RESEARCH_MORE
                rationale = f"Insufficient evidence items ({len(evidence_list)}/{min_evidence_count})."
            else:
                decision = VerificationDecision.ESCALATE
                rationale = f"Evidence count below target ({len(evidence_list)}/{min_evidence_count}) and iteration limit reached."
        elif score >= self.pass_threshold and len(conflicts) == 0:
            decision = VerificationDecision.PASS
            rationale = f"Evidence meets quality standards with score {score:.2f} >= {self.pass_threshold}."
        elif len(conflicts) > 0:
            if iteration < max_iterations:
                decision = VerificationDecision.RESEARCH_MORE
                rationale = f"Detected {len(conflicts)} contradiction(s) requiring resolution."
            else:
                decision = VerificationDecision.REVISE
                rationale = f"Unresolved contradictions present ({len(conflicts)}), flag in report synthesis."
        else:
            if iteration < max_iterations:
                decision = VerificationDecision.RESEARCH_MORE
                rationale = f"Evidence score {score:.2f} below threshold {self.pass_threshold}."
            else:
                decision = VerificationDecision.REVISE
                rationale = f"Evidence score {score:.2f} below threshold, synthesize best partial report."

        # Record metrics
        metrics.record_verification_score(score)

        logger.info(
            "Stage 1 evidence verification complete",
            decision=decision.value,
            score=score,
            evidence_count=len(evidence_list),
            conflicts=len(conflicts),
        )

        return build_verification_result(
            stage=1,
            decision=decision,
            score=score,
            claim_verdicts=verdicts,
            unsupported_claims=unsupported,
            contradictions_found=conflict_descs,
            rationale=rationale,
        )

    def verify_report(
        self,
        report: Report,
        evidence_list: List[Evidence],
    ) -> VerificationResult:
        """
        Stage 2: Audit completed report against underlying evidence.
        """
        # Extract section statements and citations
        all_section_text = " ".join(sec.content for sec in report.sections)
        # Sentence splitting for basic claim extraction
        statements = [
            s.strip() for s in all_section_text.split(".") if len(s.strip().split()) >= 6
        ]

        verdicts = self.claim_checker.check_claims(statements[:10], evidence_list)
        unsupported = [v.claim for v in verdicts if not v.supported]

        # Calculate hallucination risk based on unsupported claim ratio
        unsupported_ratio = len(unsupported) / max(len(verdicts), 1)
        hallucination_risk = round(unsupported_ratio * 0.8, 2)

        # Check citation integrity
        evidence_urls = {e.url for e in evidence_list}
        invalid_citations = [c for c in report.citations if c.url not in evidence_urls]

        # Calculate Stage 2 score
        score = calculate_quality_score(
            claim_verdicts=verdicts,
            evidence_list=evidence_list,
            contradictions_count=len(invalid_citations),
        )

        if score >= self.pass_threshold and hallucination_risk < 0.25:
            decision = VerificationDecision.PASS
            rationale = f"Report verified with high fidelity (score: {score:.2f}, risk: {hallucination_risk})."
        elif hallucination_risk >= 0.25:
            decision = VerificationDecision.REVISE
            rationale = f"High hallucination risk detected ({hallucination_risk:.2f}); revision recommended."
        else:
            decision = VerificationDecision.PASS
            rationale = f"Report accepted with warnings (score: {score:.2f})."

        logger.info(
            "Stage 2 report verification complete",
            decision=decision.value,
            score=score,
            hallucination_risk=hallucination_risk,
        )

        return build_verification_result(
            stage=2,
            decision=decision,
            score=score,
            claim_verdicts=verdicts,
            unsupported_claims=unsupported,
            hallucination_risk=hallucination_risk,
            rationale=rationale,
        )

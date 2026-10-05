"""
Quality Score Aggregator for CARA.

Aggregates multiple verification dimensions into a normalized overall score [0.0 - 1.0]:
- Claim Support Ratio (Weight: 0.35)
- Average Source Credibility (Weight: 0.25)
- Source Diversity & Count (Weight: 0.20)
- Freedom from Contradictions (Weight: 0.20)
"""

from __future__ import annotations

from typing import List
from app.schemas.evidence import Evidence
from app.schemas.verification import ClaimVerdict

WEIGHT_CLAIM_SUPPORT = 0.35
WEIGHT_CREDIBILITY = 0.25
WEIGHT_DIVERSITY = 0.20
WEIGHT_NON_CONTRADICTION = 0.20


def calculate_quality_score(
    claim_verdicts: List[ClaimVerdict],
    evidence_list: List[Evidence],
    contradictions_count: int = 0,
    min_evidence_target: int = 3,
) -> float:
    """
    Calculate composite verification quality score between 0.0 and 1.0.
    """
    # 1. Claim support ratio
    if claim_verdicts:
        supported_count = sum(1 for v in claim_verdicts if v.supported)
        claim_ratio = supported_count / len(claim_verdicts)
    else:
        claim_ratio = 1.0 if evidence_list else 0.0

    # 2. Average source credibility
    if evidence_list:
        avg_cred = sum(e.confidence for e in evidence_list) / len(evidence_list)
    else:
        avg_cred = 0.0

    # 3. Source count & diversity
    ev_count_ratio = min(len(evidence_list) / max(min_evidence_target, 1), 1.0)

    # 4. Freedom from contradictions (penalize 0.25 per conflict detected)
    non_contradiction = max(0.0, 1.0 - (contradictions_count * 0.25))

    composite = (
        WEIGHT_CLAIM_SUPPORT * claim_ratio
        + WEIGHT_CREDIBILITY * avg_cred
        + WEIGHT_DIVERSITY * ev_count_ratio
        + WEIGHT_NON_CONTRADICTION * non_contradiction
    )

    return round(max(0.0, min(composite, 1.0)), 3)

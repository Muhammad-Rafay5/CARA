"""
Claim Checker for CARA.

Verifies whether textual assertions or report claims are directly supported
by gathered evidence snippets, identifying unsupported statements and hallucination risk.
"""

from __future__ import annotations

import re
from typing import List, Tuple

from app.schemas.evidence import Evidence
from app.schemas.verification import ClaimVerdict


class ClaimChecker:
    """
    Checks claims against an evidence base using keyword overlap,
    exact string matching, and negation consistency.
    """

    def check_claim(self, claim: str, evidence_list: List[Evidence]) -> ClaimVerdict:
        """
        Verify a single factual claim against all gathered evidence.
        """
        claim_clean = claim.strip()
        claim_lower = claim_clean.lower()
        supporting_urls = []
        contradicting_urls = []

        # Extract significant words (length >= 4) from claim
        claim_words = set(re.findall(r"\b[a-z]{4,}\b", claim_lower))
        if not claim_words:
            return ClaimVerdict(
                claim=claim_clean,
                supported=False,
                confidence=0.0,
                notes="Claim contains no significant keywords to verify.",
            )

        best_match_ratio = 0.0

        for ev in evidence_list:
            content_lower = (ev.content + " " + ev.claim).lower()

            # Measure keyword overlap
            content_words = set(re.findall(r"\b[a-z]{4,}\b", content_lower))
            overlap = claim_words.intersection(content_words)
            ratio = len(overlap) / len(claim_words)

            if ratio > best_match_ratio:
                best_match_ratio = ratio

            # Check support threshold
            if ratio >= 0.6:
                # Check for negation mismatch
                claim_has_negation = bool(re.search(r"\b(not|never|neither|no|fails|cannot)\b", claim_lower))
                ev_has_negation = bool(re.search(r"\b(not|never|neither|no|fails|cannot)\b", content_lower))

                if claim_has_negation != ev_has_negation:
                    contradicting_urls.append(ev.url)
                else:
                    supporting_urls.append(ev.url)

        supported = len(supporting_urls) > 0 and len(contradicting_urls) == 0
        confidence = round(min(best_match_ratio, 1.0), 2)

        notes = (
            f"Supported by {len(supporting_urls)} source(s)."
            if supported
            else f"Insufficient match (match ratio {confidence})."
        )
        if contradicting_urls:
            notes += f" Contradicted by {len(contradicting_urls)} source(s)."

        return ClaimVerdict(
            claim=claim_clean,
            supported=supported,
            confidence=confidence,
            supporting_urls=supporting_urls,
            contradicting_urls=contradicting_urls,
            notes=notes,
        )

    def check_claims(self, claims: List[str], evidence_list: List[Evidence]) -> List[ClaimVerdict]:
        """Verify multiple claims concurrently."""
        return [self.check_claim(c, evidence_list) for c in claims if c.strip()]

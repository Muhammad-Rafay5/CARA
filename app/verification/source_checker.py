"""
Source Checker for CARA.

Verifies domain credibility, authority distribution, and diversity of sources.
Flags reliance on single unverified domains or suspicious URLs.
"""

from __future__ import annotations

from typing import Dict, List
from urllib.parse import urlparse

from app.research.source_quality import classify_source_type, get_source_credibility
from app.schemas.evidence import Evidence, SourceType


class SourceChecker:
    """
    Evaluates source diversity, average authority, and flags low-quality domains.
    """

    def check_sources(self, evidence_list: List[Evidence]) -> Dict[str, any]:
        """
        Analyze a collection of evidence sources.
        """
        if not evidence_list:
            return {
                "average_credibility": 0.0,
                "domain_count": 0,
                "authoritative_count": 0,
                "low_credibility_count": 0,
                "diversity_score": 0.0,
                "warnings": ["No evidence items available to check."],
            }

        domains = set()
        credibilities = []
        authoritative = 0
        low_credibility = 0
        warnings = []

        for ev in evidence_list:
            cred = ev.confidence
            credibilities.append(cred)

            parsed = urlparse(ev.url)
            domain = parsed.netloc or parsed.path
            domains.add(domain)

            if ev.source_type in (SourceType.OFFICIAL_DOCS, SourceType.ACADEMIC):
                authoritative += 1
            elif cred < 0.5:
                low_credibility += 1

        avg_cred = sum(credibilities) / len(credibilities) if credibilities else 0.0
        diversity = min(len(domains) / max(len(evidence_list), 1), 1.0)

        if len(domains) == 1 and len(evidence_list) > 2:
            warnings.append("All evidence originates from a single domain; lacks multi-source confirmation.")

        if low_credibility > (len(evidence_list) / 2):
            warnings.append("Over 50% of evidence items come from low-credibility sources.")

        return {
            "average_credibility": round(avg_cred, 3),
            "domain_count": len(domains),
            "authoritative_count": authoritative,
            "low_credibility_count": low_credibility,
            "diversity_score": round(diversity, 3),
            "warnings": warnings,
        }

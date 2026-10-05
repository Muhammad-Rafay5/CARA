"""
Contradiction Detection Engine for CARA.

Cross-examines evidence items collected from different sources to detect
potential factual discrepancies, opposing claims, or conflicting figures.
"""

from __future__ import annotations

import re
from typing import List, Tuple
from dataclasses import dataclass

from app.schemas.evidence import Evidence
from app.observability.logging import get_logger

logger = get_logger(__name__)

# Disagreement or opposition markers in text
CONTRADICTION_SIGNALS = [
    r"\bhowever\b", r"\bin contrast\b", r"\bon the contrary\b",
    r"\bcontrary to\b", r"\bdisputed\b", r"\bdisagree\b",
    r"\bconflict\b", r"\bunlike\b", r"\bdebunked\b",
    r"\bfalse\b", r"\bincorrect\b", r"\bnot true\b",
]


@dataclass
class ContradictionRecord:
    evidence_a: Evidence
    evidence_b: Evidence
    discrepancy_description: str
    confidence: float


class ContradictionDetector:
    """
    Detects potential contradictions between gathered evidence items.
    """

    def detect_conflicts(self, evidence_list: List[Evidence]) -> List[ContradictionRecord]:
        """
        Compare evidence pairs for mutual contradictions or conflicting signals.
        """
        conflicts: List[ContradictionRecord] = []
        n = len(evidence_list)

        if n < 2:
            return []

        for i in range(n):
            for j in range(i + 1, n):
                ev1 = evidence_list[i]
                ev2 = evidence_list[j]

                # Don't compare evidence from the identical source URL
                if ev1.url == ev2.url:
                    continue

                conflict = self._check_pair(ev1, ev2)
                if conflict:
                    conflicts.append(conflict)

        if conflicts:
            logger.warning("Contradictions detected between sources", count=len(conflicts))

        return conflicts

    def _check_pair(self, ev1: Evidence, ev2: Evidence) -> ContradictionRecord | None:
        """
        Check if two evidence pieces contradict each other.
        """
        text1 = (ev1.claim + " " + ev1.content).lower()
        text2 = (ev2.claim + " " + ev2.content).lower()

        # Check for direct numerical conflict on same topic keywords
        words1 = set(re.findall(r"\b[a-z]{4,}\b", text1))
        words2 = set(re.findall(r"\b[a-z]{4,}\b", text2))
        overlap = words1.intersection(words2)

        # High keyword overlap suggests they address the same topic
        if len(overlap) >= 4:
            # Check for negation words in one but not the other
            has_negation_1 = bool(re.search(r"\b(not|never|neither|no|fails|cannot)\b", text1))
            has_negation_2 = bool(re.search(r"\b(not|never|neither|no|fails|cannot)\b", text2))

            if has_negation_1 != has_negation_2:
                for sig in CONTRADICTION_SIGNALS:
                    if re.search(sig, text1) or re.search(sig, text2):
                        return ContradictionRecord(
                            evidence_a=ev1,
                            evidence_b=ev2,
                            discrepancy_description=f"Potential polarity / factual conflict regarding common topics: {list(overlap)[:3]}",
                            confidence=0.7,
                        )

        return None

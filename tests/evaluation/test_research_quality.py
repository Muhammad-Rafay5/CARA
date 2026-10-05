"""
Evaluation benchmark for Research Quality and Citation Completeness.
"""

import pytest
from app.schemas.evidence import Evidence
from app.verification.verifier import Verifier


def test_research_quality_benchmark():
    verifier = Verifier()
    evidence = [
        Evidence(
            claim="Python 3.12 introduces per-interpreter GIL",
            content="PEP 684 per-interpreter GIL introduces subinterpreters with individual locks.",
            url="https://docs.python.org/3/whatsnew/3.12.html",
            confidence=1.0,
        ),
        Evidence(
            claim="Subinterpreters allow true multicore CPU parallelism",
            content="Subinterpreters enable running Python code in parallel without a shared global lock.",
            url="https://peps.python.org/pep-0684/",
            confidence=0.95,
        ),
    ]

    result = verifier.verify_evidence(
        query="Python 3.12 subinterpreters and per-interpreter GIL",
        evidence_list=evidence,
        min_evidence_count=2,
    )
    assert result.score >= 0.75
    assert result.decision.value == "PASS"

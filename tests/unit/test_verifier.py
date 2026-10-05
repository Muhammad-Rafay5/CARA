"""
Unit tests for Verifier and Claim Checker.
"""

from app.schemas.evidence import Evidence, SourceType
from app.verification.claim_checker import ClaimChecker
from app.verification.verifier import Verifier


def test_claim_checker_exact_and_negation():
    checker = ClaimChecker()
    ev = Evidence(
        claim="PostgreSQL supports ACID transactions",
        content="PostgreSQL provides full ACID compliance and transactional guarantees.",
        url="https://postgresql.org",
        confidence=1.0,
    )

    verdict_supported = checker.check_claim("PostgreSQL provides full ACID compliance", [ev])
    assert verdict_supported.supported is True
    assert verdict_supported.confidence >= 0.6

    verdict_negated = checker.check_claim("PostgreSQL does not support ACID compliance", [ev])
    assert verdict_negated.supported is False


def test_verifier_stage_1():
    verifier = Verifier()
    ev = Evidence(
        claim="FastAPI is an async web framework",
        content="FastAPI is a modern high performance web framework for building APIs with Python.",
        url="https://fastapi.tiangolo.com",
        source_type=SourceType.OFFICIAL_DOCS,
        confidence=1.0,
    )

    res = verifier.verify_evidence(
        query="FastAPI web framework",
        evidence_list=[ev, ev, ev],
        iteration=1,
        max_iterations=3,
        min_evidence_count=2,
    )
    assert res.stage == 1
    assert res.score > 0.7

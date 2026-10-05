"""
Integration test for Verification & Targeted Recovery Loop.
"""

import pytest
from app.agent.nodes.verify_research import verify_research
from app.schemas.evidence import Evidence
from app.schemas.research import ResearchState


@pytest.mark.asyncio
async def test_verification_loop_execution():
    state = ResearchState(
        query="Test database concurrency",
        evidence_items=[
            {
                "claim": "Concurrency in databases",
                "content": "Databases handle concurrency via locks or MVCC.",
                "url": "https://postgresql.org",
                "confidence": 1.0,
            }
        ],
    )
    res_state = await verify_research(state)
    assert res_state.verification_status is not None
    assert res_state.verification_score is not None

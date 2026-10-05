"""
Integration test for full LangGraph Agent Workflow.
"""

import pytest
from app.agent.graph import research_graph
from app.schemas.research import ResearchDepth, ResearchState, ResearchStatus


@pytest.mark.asyncio
async def test_end_to_end_research_graph():
    initial_state = ResearchState(
        query="Python asyncio event loop mechanics",
        depth=ResearchDepth.QUICK,
    )
    result = await research_graph.ainvoke(initial_state)

    if isinstance(result, dict):
        status = result.get("status")
        report = result.get("report")
    else:
        status = result.status
        report = result.report

    assert status == ResearchStatus.COMPLETED
    assert report is not None
    assert len(report) > 200  # Offline tests produce shorter reports; validate structure exists

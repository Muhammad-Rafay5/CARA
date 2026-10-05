"""
Evaluation benchmark for Agent Reliability under simulated stress & loop bounds.
"""

import pytest
from app.optimization.budget_manager import BudgetManager
from app.recovery.manager import RecoveryManager
from app.schemas.research import ResearchState


def test_agent_hard_guardrail_enforcement():
    bm = BudgetManager()

    # Simulate run at max tool call boundary
    state = ResearchState(
        tool_calls=20,
        max_tool_calls=20,
    )
    ok, reason = bm.check_budget(state)
    assert ok is False
    assert "Tool call quota" in reason


def test_agent_consecutive_failure_containment():
    rm = RecoveryManager()
    state = ResearchState(max_iterations=3)

    # Simulate 3 consecutive timeout exceptions
    for i in range(3):
        action = rm.handle_failure(TimeoutError("Timeout"), state)

    # After exhausting max attempts, recovery escalates to partial result
    assert state.warnings is not None
    assert len(state.warnings) == 3

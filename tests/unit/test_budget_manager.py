"""
Unit tests for BudgetManager and guardrail triggers.
"""

import pytest
from app.core.exceptions import BudgetExceededError
from app.optimization.budget_manager import BudgetManager
from app.schemas.research import ResearchState


def test_budget_manager_within_limits():
    bm = BudgetManager()
    state = ResearchState(iteration=1, model_calls=2, tool_calls=3, tokens_used=4000)
    ok, reason = bm.check_budget(state)
    assert ok is True
    assert reason == ""


def test_budget_manager_exceeded():
    bm = BudgetManager()
    state = ResearchState(iteration=3, max_iterations=3)
    ok, reason = bm.check_budget(state)
    assert ok is False
    assert "Iteration limit" in reason

    with pytest.raises(BudgetExceededError):
        bm.enforce_or_raise(state)

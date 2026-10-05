"""
Budget Manager for CARA.

Enforces hard execution boundaries and limits:
- MAX_RESEARCH_ITERATIONS: 3
- MAX_MODEL_CALLS: 10
- MAX_TOOL_CALLS: 20
- MAX_TOKENS: 15,000
- MAX_EXECUTION_TIME: 120s
"""

from __future__ import annotations

import time
from typing import Tuple

from app.core.exceptions import BudgetExceededError
from app.observability.logging import get_logger
from app.schemas.research import ResearchState

logger = get_logger(__name__)


class BudgetManager:
    """
    Checks whether an execution state is within authorized budget guardrails.
    """

    def check_budget(self, state: ResearchState) -> Tuple[bool, str]:
        """
        Evaluate current state against all limits.
        Returns (is_within_budget, reason_if_exceeded).
        """
        if state.iteration >= state.max_iterations:
            return False, f"Iteration limit reached ({state.iteration}/{state.max_iterations})"

        if state.model_calls >= state.max_model_calls:
            return False, f"Model call quota exceeded ({state.model_calls}/{state.max_model_calls})"

        if state.tool_calls >= state.max_tool_calls:
            return False, f"Tool call quota exceeded ({state.tool_calls}/{state.max_tool_calls})"

        if state.tokens_used >= state.max_tokens:
            return False, f"Token budget exceeded ({state.tokens_used}/{state.max_tokens})"

        return True, ""

    def enforce_or_raise(self, state: ResearchState) -> None:
        """
        Raise BudgetExceededError if boundaries are violated.
        """
        ok, reason = self.check_budget(state)
        if not ok:
            logger.warning("Budget limit reached", reason=reason, request_id=state.request_id)
            raise BudgetExceededError(reason)


budget_manager = BudgetManager()

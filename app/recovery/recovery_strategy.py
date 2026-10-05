"""
Targeted Recovery Strategy Hierarchy for CARA.

Ordered recovery escalation steps:
1. LOCAL_REPAIR: Re-evaluate or repair specific claim without re-running entire pipeline.
2. RETRY_OPERATION: Transient failure → retry with exponential backoff.
3. REFORMULATE_QUERY: No results / gap → generate alternative query phrasing.
4. CHANGE_TOOL: Current tool failed or insufficient → switch to backup tool.
5. CHANGE_MODEL: Current model rate-limited / degraded → switch via fallback chain.
6. REDUCE_SCOPE: Budget running low → focus strictly on core user query.
7. PARTIAL_RESULT: Limits exhausted → produce partial output with clear disclosure warning.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional

from app.observability.logging import get_logger
from app.recovery.failure_classifier import FailureType

logger = get_logger(__name__)


class RecoveryAction(str, Enum):
    LOCAL_REPAIR = "LOCAL_REPAIR"
    RETRY_OPERATION = "RETRY_OPERATION"
    REFORMULATE_QUERY = "REFORMULATE_QUERY"
    CHANGE_TOOL = "CHANGE_TOOL"
    CHANGE_MODEL = "CHANGE_MODEL"
    REDUCE_SCOPE = "REDUCE_SCOPE"
    PARTIAL_RESULT = "PARTIAL_RESULT"


class RecoveryStrategy:
    """
    Selects the most targeted, lowest-cost recovery action based on failure type and context.
    """

    def select_action(
        self,
        failure_type: FailureType,
        attempt: int = 1,
        max_attempts: int = 3,
    ) -> RecoveryAction:
        """
        Map failure type and retry depth to recovery action.
        """
        if failure_type == FailureType.RATE_LIMIT:
            if attempt < max_attempts:
                return RecoveryAction.CHANGE_MODEL
            return RecoveryAction.PARTIAL_RESULT

        elif failure_type == FailureType.MODEL_ERROR:
            return RecoveryAction.CHANGE_MODEL

        elif failure_type == FailureType.NO_SEARCH_RESULTS:
            if attempt < max_attempts:
                return RecoveryAction.REFORMULATE_QUERY
            return RecoveryAction.CHANGE_TOOL

        elif failure_type == FailureType.TOOL_ERROR:
            return RecoveryAction.CHANGE_TOOL

        elif failure_type == FailureType.UNSUPPORTED_CLAIM:
            return RecoveryAction.LOCAL_REPAIR

        elif failure_type == FailureType.CONTRADICTION:
            return RecoveryAction.LOCAL_REPAIR

        elif failure_type == FailureType.INSUFFICIENT_EVIDENCE:
            if attempt < max_attempts:
                return RecoveryAction.REFORMULATE_QUERY
            return RecoveryAction.REDUCE_SCOPE

        elif failure_type == FailureType.BUDGET_EXCEEDED:
            return RecoveryAction.PARTIAL_RESULT

        elif failure_type == FailureType.TIMEOUT:
            return RecoveryAction.PARTIAL_RESULT

        return RecoveryAction.RETRY_OPERATION

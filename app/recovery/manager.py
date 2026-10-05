"""
Recovery Manager for CARA.

Coordinates recovery actions without restarting the entire research loop:
- Tracks failure history per request
- Applies targeted patches (repairing specific claims, query reformulation, provider switching)
- Prevents infinite loops through hard attempt caps
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.observability.logging import get_logger
from app.recovery.failure_classifier import FailureClassifier, FailureType
from app.recovery.recovery_strategy import RecoveryAction, RecoveryStrategy
from app.schemas.research import ResearchState

logger = get_logger(__name__)


class RecoveryManager:
    """
    Coordinates targeted recovery workflows.
    """

    def __init__(
        self,
        classifier: Optional[FailureClassifier] = None,
        strategy: Optional[RecoveryStrategy] = None,
    ):
        self.classifier = classifier or FailureClassifier()
        self.strategy = strategy or RecoveryStrategy()
        self._failure_counts: Dict[str, int] = {}

    def handle_failure(
        self,
        error_or_issue: Any,
        state: ResearchState,
    ) -> RecoveryAction:
        """
        Evaluate failure and determine targeted recovery action.
        """
        if isinstance(error_or_issue, Exception):
            failure_type = self.classifier.classify_exception(error_or_issue)
            issue_key = f"{failure_type.value}:{type(error_or_issue).__name__}"
        else:
            failure_type = self.classifier.classify_verification(error_or_issue)
            issue_key = f"{failure_type.value}:verification"

        count = self._failure_counts.get(issue_key, 0) + 1
        self._failure_counts[issue_key] = count

        action = self.strategy.select_action(
            failure_type=failure_type,
            attempt=count,
            max_attempts=state.max_iterations,
        )

        logger.info(
            "Targeted recovery action selected",
            failure_type=failure_type.value,
            attempt=count,
            action=action.value,
        )

        # Record warning in agent state
        state.warnings.append(
            f"Encountered {failure_type.value} (attempt {count}). Applying recovery: {action.value}."
        )

        return action

    def get_reformulated_query(self, original_query: str, unsupported_claim: Optional[str] = None) -> str:
        """
        Generate targeted search query to address specific gap.
        """
        if unsupported_claim:
            return f"{unsupported_claim} fact check authoritative"
        return f"{original_query} technical details documentation"

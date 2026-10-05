"""
Classify Failure Graph Node for CARA.

Determines the root cause category when verification does not pass or errors occur.
"""

from __future__ import annotations

from app.observability.logging import get_logger
from app.recovery.failure_classifier import FailureClassifier, FailureType
from app.schemas.research import ResearchState

logger = get_logger(__name__)
classifier = FailureClassifier()


async def classify_failure(state: ResearchState) -> ResearchState:
    """Classify verification shortfall or error into standardized taxonomy."""
    status = state.verification_status or "UNKNOWN"
    failure_record = {
        "iteration": state.iteration,
        "verification_status": status,
        "score": state.verification_score,
        "unsupported_claims": state.unsupported_claims,
    }
    state.failure_history.append(failure_record)

    logger.warning("Classified failure for targeted recovery", failure=failure_record)
    return state

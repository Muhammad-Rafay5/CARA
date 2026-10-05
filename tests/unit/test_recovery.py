"""
Unit tests for Failure Classifier and Recovery Manager.
"""

from app.recovery.failure_classifier import FailureClassifier, FailureType
from app.recovery.manager import RecoveryManager
from app.recovery.recovery_strategy import RecoveryAction
from app.schemas.research import ResearchState


def test_failure_classifier_exceptions():
    fc = FailureClassifier()
    assert fc.classify_exception(TimeoutError("Deadline exceeded")) == FailureType.TIMEOUT


def test_recovery_manager_workflow():
    rm = RecoveryManager()
    state = ResearchState(max_iterations=3)

    action = rm.handle_failure(TimeoutError("Request timed out"), state)
    assert action in (RecoveryAction.PARTIAL_RESULT, RecoveryAction.RETRY_OPERATION)

    ref = rm.get_reformulated_query("PostgreSQL vs MySQL", "performance metrics")
    assert "performance metrics" in ref

"""
Unit tests for Circuit Breaker and Provider Health monitoring.
"""

import pytest
from app.core.exceptions import ProviderUnavailableError
from app.recovery.circuit_breaker import CircuitBreaker, CircuitState


def test_circuit_breaker_transitions():
    cb = CircuitBreaker(name="test_provider", failure_threshold=2, cooldown_seconds=0.1)

    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True

    # Record 1 failure -> still closed
    cb.record_failure(Exception("Fail 1"))
    assert cb.state == CircuitState.CLOSED

    # Record 2nd failure -> trips to OPEN
    cb.record_failure(Exception("Fail 2"))
    assert cb.state == CircuitState.OPEN
    assert cb.can_execute() is False

    with pytest.raises(ProviderUnavailableError):
        cb.check_or_raise()

    # Wait for cooldown
    import time
    time.sleep(0.15)

    # Evaluates to HALF_OPEN
    assert cb.state == CircuitState.HALF_OPEN
    assert cb.can_execute() is True

    # Record success -> resets to CLOSED
    cb.record_success()
    assert cb.state == CircuitState.CLOSED

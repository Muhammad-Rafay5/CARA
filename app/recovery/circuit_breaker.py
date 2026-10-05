"""
Circuit Breaker Pattern implementation for model providers in CARA.

Maintains state:
    CLOSED: Calls are allowed through normally.
    OPEN: Calls are immediately blocked (fails fast) when failure threshold exceeded.
    HALF_OPEN: Test calls are allowed through after cooldown window expires.

Transitions:
    CLOSED -> OPEN: Consecutive failures >= failure_threshold.
    OPEN -> HALF_OPEN: Current time >= last_failure_time + cooldown_seconds.
    HALF_OPEN -> CLOSED: On successful test call.
    HALF_OPEN -> OPEN: On failed test call.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Dict, Optional

from app.core.constants import (
    CIRCUIT_BREAKER_COOLDOWN_SECONDS,
    CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    CIRCUIT_BREAKER_HALF_OPEN_CALLS,
)
from app.core.exceptions import ProviderUnavailableError
from app.observability.logging import get_logger

logger = get_logger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    In-memory, thread-safe circuit breaker for a single target/provider.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = CIRCUIT_BREAKER_FAILURE_THRESHOLD,
        cooldown_seconds: float = CIRCUIT_BREAKER_COOLDOWN_SECONDS,
        half_open_calls: int = CIRCUIT_BREAKER_HALF_OPEN_CALLS,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.half_open_calls = half_open_calls

        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._last_state_change = time.time()
        self._last_failure_time: Optional[float] = None
        self._half_open_attempt_count = 0

    @property
    def state(self) -> CircuitState:
        """Evaluate and return current state, checking for timeout transitions."""
        if self._state == CircuitState.OPEN:
            elapsed = time.time() - (self._last_failure_time or self._last_state_change)
            if elapsed >= self.cooldown_seconds:
                self._transition_to(CircuitState.HALF_OPEN)
        return self._state

    def _transition_to(self, new_state: CircuitState) -> None:
        old_state = self._state
        self._state = new_state
        self._last_state_change = time.time()
        if new_state == CircuitState.HALF_OPEN:
            self._half_open_attempt_count = 0
        logger.info(
            "Circuit breaker state transition",
            name=self.name,
            old_state=old_state.value,
            new_state=new_state.value,
        )

    def can_execute(self) -> bool:
        """Check if an execution attempt is permitted."""
        current_state = self.state
        if current_state == CircuitState.CLOSED:
            return True
        elif current_state == CircuitState.HALF_OPEN:
            if self._half_open_attempt_count < self.half_open_calls:
                self._half_open_attempt_count += 1
                return True
            return False
        else:  # OPEN
            return False

    def record_success(self) -> None:
        """Record a successful call, resetting failure counts."""
        if self.state == CircuitState.HALF_OPEN:
            self._transition_to(CircuitState.CLOSED)
        self._consecutive_failures = 0

    def record_failure(self, error: Optional[Exception] = None) -> None:
        """Record a failed call, potentially tripping the circuit."""
        self._consecutive_failures += 1
        self._last_failure_time = time.time()

        logger.warning(
            "Circuit breaker recorded failure",
            name=self.name,
            consecutive_failures=self._consecutive_failures,
            threshold=self.failure_threshold,
            error=str(error) if error else None,
        )

        if self._state == CircuitState.HALF_OPEN:
            self._transition_to(CircuitState.OPEN)
        elif self._consecutive_failures >= self.failure_threshold:
            self._transition_to(CircuitState.OPEN)

    def check_or_raise(self) -> None:
        """
        Verify if calls are allowed; raise ProviderUnavailableError if OPEN.
        """
        if not self.can_execute():
            raise ProviderUnavailableError(self.name)


class CircuitBreakerRegistry:
    """Registry maintaining circuit breakers per provider name."""

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}

    def get(self, name: str) -> CircuitBreaker:
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name=name)
        return self._breakers[name]

    def reset_all(self) -> None:
        self._breakers.clear()


circuit_breakers = CircuitBreakerRegistry()

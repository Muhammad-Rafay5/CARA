"""
Recovery subsystem for CARA.

Exports:
- CircuitBreaker, CircuitBreakerRegistry, circuit_breakers
- FailureClassifier, FailureType
- RecoveryStrategy, RecoveryAction
- RecoveryManager
- RetryPolicy
"""

from app.recovery.circuit_breaker import CircuitBreaker, CircuitBreakerRegistry, circuit_breakers
from app.recovery.failure_classifier import FailureClassifier, FailureType
from app.recovery.manager import RecoveryManager
from app.recovery.recovery_strategy import RecoveryAction, RecoveryStrategy
from app.recovery.retry_policy import RetryPolicy

__all__ = [
    "CircuitBreaker",
    "CircuitBreakerRegistry",
    "FailureClassifier",
    "FailureType",
    "RecoveryAction",
    "RecoveryManager",
    "RecoveryStrategy",
    "RetryPolicy",
    "circuit_breakers",
]

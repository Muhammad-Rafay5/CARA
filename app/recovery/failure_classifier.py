"""
Failure Classifier for CARA.

Classifies errors and verification roadblocks into a canonical taxonomy:
- MODEL_ERROR: Upstream model provider failures or schema errors.
- RATE_LIMIT: HTTP 429 rate limit or quota exhaustion.
- TOOL_ERROR: Tool execution runtime errors.
- NO_SEARCH_RESULTS: Web search or document search yielded 0 items.
- INSUFFICIENT_EVIDENCE: Evidence collected is below threshold or lacks depth.
- CONTRADICTION: Conflicting facts detected between authoritative sources.
- UNSUPPORTED_CLAIM: Specific claim cannot be verified against evidence.
- BUDGET_EXCEEDED: Token limit, tool call quota, or iteration cap reached.
- TIMEOUT: Operation exceeded execution time limits.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from app.core.exceptions import (
    BudgetExceededError,
    ModelProviderError,
    RateLimitError,
    SSRFBlockedError,
    ToolExecutionError,
)
from app.schemas.verification import VerificationDecision, VerificationResult


class FailureType(str, Enum):
    MODEL_ERROR = "MODEL_ERROR"
    RATE_LIMIT = "RATE_LIMIT"
    TOOL_ERROR = "TOOL_ERROR"
    NO_SEARCH_RESULTS = "NO_SEARCH_RESULTS"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONTRADICTION = "CONTRADICTION"
    UNSUPPORTED_CLAIM = "UNSUPPORTED_CLAIM"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    TIMEOUT = "TIMEOUT"
    UNKNOWN = "UNKNOWN"


class FailureClassifier:
    """
    Diagnoses exceptions and verification outcomes into standardized FailureType enums.
    """

    def classify_exception(self, exc: Exception) -> FailureType:
        """Categorize a runtime exception."""
        if isinstance(exc, RateLimitError):
            return FailureType.RATE_LIMIT
        if isinstance(exc, BudgetExceededError):
            return FailureType.BUDGET_EXCEEDED
        if isinstance(exc, (ToolExecutionError, SSRFBlockedError)):
            return FailureType.TOOL_ERROR
        if isinstance(exc, ModelProviderError):
            return FailureType.MODEL_ERROR
        if isinstance(exc, TimeoutError):
            return FailureType.TIMEOUT

        msg = str(exc).lower()
        if "429" in msg or "rate limit" in msg:
            return FailureType.RATE_LIMIT
        if "budget" in msg or "maximum" in msg:
            return FailureType.BUDGET_EXCEEDED
        if "timeout" in msg or "timed out" in msg:
            return FailureType.TIMEOUT

        return FailureType.UNKNOWN

    def classify_verification(self, result: VerificationResult) -> FailureType:
        """Categorize verification issues."""
        if result.decision == VerificationDecision.PASS:
            return FailureType.UNKNOWN

        if result.contradictions_found:
            return FailureType.CONTRADICTION

        if result.unsupported_claims:
            return FailureType.UNSUPPORTED_CLAIM

        if result.decision == VerificationDecision.RESEARCH_MORE:
            return FailureType.INSUFFICIENT_EVIDENCE

        return FailureType.INSUFFICIENT_EVIDENCE

"""
Error payload schemas for CARA.
Standardized error response structure preventing stack trace leaks.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    # Client errors
    INVALID_REQUEST = "INVALID_REQUEST"
    QUERY_TOO_SHORT = "QUERY_TOO_SHORT"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    RATE_LIMITED = "RATE_LIMITED"

    # Agent/model errors
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    ALL_PROVIDERS_FAILED = "ALL_PROVIDERS_FAILED"
    TOOL_EXECUTION_FAILED = "TOOL_EXECUTION_FAILED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

    # System errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    TIMEOUT = "TIMEOUT"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"


class ErrorDetail(BaseModel):
    """A single structured error entry."""

    field: str | None = None
    message: str
    code: ErrorCode


class ErrorResponse(BaseModel):
    """
    Standardized error envelope returned on API failures.

    IMPORTANT: Never include raw exception messages, tracebacks, or
    internal system paths in the 'errors' or 'message' fields.
    All error messages must be safe for external consumption.
    """

    success: bool = False
    message: str = Field(
        ...,
        description="Human-readable error summary (external-safe).",
    )
    error_code: ErrorCode
    errors: list[ErrorDetail] = Field(default_factory=list)
    request_id: str = ""
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional non-sensitive debug metadata.",
    )

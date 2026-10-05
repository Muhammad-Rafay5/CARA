"""
API response envelope and model metadata schemas for CARA.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """
    Standard JSON response envelope for all CARA REST endpoints.

    Example:
        {
            "success": true,
            "data": { ... },
            "message": "Research completed successfully.",
            "request_id": "abc-123"
        }
    """

    success: bool
    data: T | None = None
    message: str = ""
    request_id: str = ""
    warnings: list[str] = Field(default_factory=list)


class ModelInfo(BaseModel):
    """Metadata about an available LLM model."""

    provider: str
    model_name: str
    tier: str  # "fast" | "standard" | "advanced"
    context_window: int
    supports_tools: bool = False
    cost_per_1k_input_tokens: float = 0.0
    cost_per_1k_output_tokens: float = 0.0
    is_available: bool = True
    is_local: bool = False


class HealthStatus(BaseModel):
    """Health check response payload."""

    status: str  # "healthy" | "degraded" | "unhealthy"
    version: str = "0.1.0"
    providers: dict[str, bool] = Field(
        default_factory=dict,
        description="Provider name → availability map.",
    )
    details: dict[str, Any] = Field(default_factory=dict)


class UsageMetrics(BaseModel):
    """Operational usage summary for metrics endpoint."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens_used: int = 0
    total_cost_usd: float = 0.0
    total_model_calls: int = 0
    total_tool_calls: int = 0
    average_verification_score: float = 0.0
    uptime_seconds: float = 0.0

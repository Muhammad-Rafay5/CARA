"""
Research request/response/state schemas for CARA.
All models use Pydantic v2 with strict validation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResearchDepth(str, Enum):
    QUICK = "quick"       # 1 iteration, lightweight model
    STANDARD = "standard" # up to 2 iterations
    DEEP = "deep"         # up to 3 iterations, strongest model


class ResearchComplexity(str, Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


class ResearchStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    BUDGET_EXCEEDED = "budget_exceeded"
    PARTIAL = "partial"


class ResearchRequest(BaseModel):
    """Input payload for a new research task."""

    query: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="The research question or topic to investigate.",
    )
    depth: ResearchDepth = Field(
        default=ResearchDepth.STANDARD,
        description="Research depth controlling iteration count and model tier.",
    )
    max_tokens_override: int | None = Field(
        default=None,
        ge=500,
        le=15000,
        description="Optional per-request token budget override.",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional caller-provided context to seed the research.",
    )

    @field_validator("query")
    @classmethod
    def query_must_not_be_whitespace(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Query must contain non-whitespace characters.")
        return v.strip()


class ResearchResponse(BaseModel):
    """Final output returned from a completed research task."""

    request_id: str
    status: ResearchStatus
    report: str | None = None
    summary: str | None = None
    verification_score: float | None = Field(default=None, ge=0.0, le=1.0)
    total_tokens_used: int = 0
    total_model_calls: int = 0
    total_tool_calls: int = 0
    total_cost_usd: float = 0.0
    iterations_completed: int = 0
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


class ResearchState(BaseModel):
    """
    Mutable agent execution state threaded through the LangGraph nodes.

    This is the single shared context object passed between graph nodes.
    Hard limits are read from AppSettings at startup and stored here for
    quick access without repeated settings singleton calls.
    """

    # Identity
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    depth: ResearchDepth = ResearchDepth.STANDARD
    status: ResearchStatus = ResearchStatus.PENDING

    # Planning
    complexity: ResearchComplexity | None = None
    research_plan: list[str] = Field(default_factory=list)
    current_step: int = 0

    # Model selection
    selected_model: str | None = None
    selected_provider: str | None = None

    # Research execution
    tool_outputs: list[dict[str, Any]] = Field(default_factory=list)
    evidence_items: list[dict[str, Any]] = Field(default_factory=list)
    iteration: int = 0

    # Verification
    verification_score: float | None = None
    verification_status: str | None = None  # PASS | RESEARCH_MORE | REVISE | ESCALATE
    unsupported_claims: list[str] = Field(default_factory=list)

    # Final output
    report: str | None = None
    summary: str | None = None

    # Resource accounting
    model_calls: int = 0
    tool_calls: int = 0
    tokens_used: int = 0
    cost_usd: float = 0.0
    warnings: list[str] = Field(default_factory=list)

    # Hard limits (populated from settings at graph startup)
    max_iterations: int = 3
    max_model_calls: int = 10
    max_tool_calls: int = 20
    max_tokens: int = 15000

    # Failure tracking
    failure_history: list[dict[str, Any]] = Field(default_factory=list)
    last_error: str | None = None

    # Timestamps
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

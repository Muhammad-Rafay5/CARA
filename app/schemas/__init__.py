"""Schemas package for CARA."""

from app.schemas.errors import ErrorCode, ErrorDetail, ErrorResponse
from app.schemas.evidence import Evidence, EvidenceStatus, SourceType
from app.schemas.models import APIResponse, HealthStatus, ModelInfo, UsageMetrics
from app.schemas.report import Citation, Report, ReportSection
from app.schemas.research import (
    ResearchComplexity,
    ResearchDepth,
    ResearchRequest,
    ResearchResponse,
    ResearchState,
    ResearchStatus,
)
from app.schemas.verification import (
    ClaimVerdict,
    VerificationDecision,
    VerificationResult,
)

__all__ = [
    "APIResponse",
    "Citation",
    "ClaimVerdict",
    "ErrorCode",
    "ErrorDetail",
    "ErrorResponse",
    "Evidence",
    "EvidenceStatus",
    "HealthStatus",
    "ModelInfo",
    "Report",
    "ReportSection",
    "ResearchComplexity",
    "ResearchDepth",
    "ResearchRequest",
    "ResearchResponse",
    "ResearchState",
    "ResearchStatus",
    "SourceType",
    "UsageMetrics",
    "VerificationDecision",
    "VerificationResult",
]

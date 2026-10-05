"""
Evidence schema for CARA.
Structured representation of a single piece of research evidence.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class SourceType(str, Enum):
    OFFICIAL_DOCS = "official_docs"   # Highest credibility
    ACADEMIC = "academic"             # Peer-reviewed / arXiv
    NEWS = "news"                     # Established news sources
    BLOG = "blog"                     # Technical blogs
    GITHUB = "github"                 # GitHub repos / code
    FORUM = "forum"                   # Stack Overflow, Reddit
    UNKNOWN = "unknown"               # Unclassified


class EvidenceStatus(str, Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    CONTRADICTED = "contradicted"
    INSUFFICIENT = "insufficient"


class Evidence(BaseModel):
    """
    A single piece of research evidence linking a claim to its source.

    Credibility hierarchy:
    OFFICIAL_DOCS (1.0) > ACADEMIC (0.9) > NEWS (0.7) > GITHUB (0.7)
                        > BLOG (0.5) > FORUM (0.4) > UNKNOWN (0.2)
    """

    claim: str = Field(
        ...,
        min_length=5,
        description="The specific factual claim this evidence supports.",
    )
    content: str = Field(
        ...,
        description="Raw extracted text supporting the claim.",
    )
    url: str = Field(
        ...,
        description="Source URL where this evidence was found.",
    )
    title: str = Field(
        default="",
        description="Page or document title.",
    )
    source_type: SourceType = Field(
        default=SourceType.UNKNOWN,
        description="Classified source category.",
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Source credibility score (0.0 – 1.0).",
    )
    status: EvidenceStatus = Field(
        default=EvidenceStatus.UNVERIFIED,
        description="Verification lifecycle status.",
    )
    citations: list[str] = Field(
        default_factory=list,
        description="Additional supporting URLs for this claim.",
    )
    tool_used: str = Field(
        default="",
        description="The tool that retrieved this evidence (e.g., 'web_search').",
    )
    retrieved_at: str = Field(
        default="",
        description="ISO 8601 timestamp when this evidence was collected.",
    )

    @property
    def credibility_score(self) -> float:
        """Map source_type to a base credibility weight."""
        weights = {
            SourceType.OFFICIAL_DOCS: 1.0,
            SourceType.ACADEMIC: 0.9,
            SourceType.NEWS: 0.7,
            SourceType.GITHUB: 0.7,
            SourceType.BLOG: 0.5,
            SourceType.FORUM: 0.4,
            SourceType.UNKNOWN: 0.2,
        }
        return weights.get(self.source_type, 0.2)

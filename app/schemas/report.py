"""
Report schema for CARA.
Structured output model for generated research reports.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """A numbered citation entry in a report."""

    number: int
    url: str
    title: str = ""
    source_type: str = "unknown"


class ReportSection(BaseModel):
    """A single titled section within the research report."""

    heading: str
    content: str
    citations: list[int] = Field(
        default_factory=list,
        description="Citation numbers referenced in this section.",
    )


class Report(BaseModel):
    """
    Fully structured research report ready for rendering.

    The report is generated AFTER two-stage verification passes.
    All claims must be traceable to evidence via citations.
    """

    title: str = Field(..., description="Auto-generated report title.")
    summary: str = Field(
        ...,
        min_length=50,
        description="Executive summary (2-5 sentences).",
    )
    sections: list[ReportSection] = Field(
        default_factory=list,
        description="Ordered list of report sections.",
    )
    citations: list[Citation] = Field(
        default_factory=list,
        description="Numbered citation list (matches in-text [N] references).",
    )
    verification_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Final verification quality score.",
    )
    complexity: str = Field(default="", description="Query complexity level used.")
    model_used: str = Field(default="", description="Primary LLM used for generation.")
    total_tokens: int = Field(default=0, description="Total tokens consumed.")
    total_cost_usd: float = Field(default=0.0, description="Estimated cost in USD.")
    iterations: int = Field(default=1, description="Number of research iterations.")
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal quality warnings from verification.",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_markdown(self) -> str:
        """Render the report as a markdown string."""
        lines: list[str] = [f"# {self.title}\n", f"{self.summary}\n"]

        for section in self.sections:
            lines.append(f"\n## {section.heading}\n")
            lines.append(section.content)

        if self.citations:
            lines.append("\n## References\n")
            for cite in self.citations:
                lines.append(f"[{cite.number}] {cite.title} — {cite.url}")

        if self.warnings:
            lines.append("\n---\n> **Quality Warnings**")
            for w in self.warnings:
                lines.append(f"> - {w}")

        return "\n".join(lines)

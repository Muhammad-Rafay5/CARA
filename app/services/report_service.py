"""
Report Service for CARA.

Handles document rendering, formatting, and file exports (Markdown, JSON, text).
"""

from __future__ import annotations

from typing import Dict, Optional
from app.schemas.report import Report


class ReportService:
    """
    Handles report formatting and rendering.
    """

    def format_as_markdown(self, report_data: Dict) -> str:
        """Render report dictionary as clean GitHub-flavored Markdown."""
        title = report_data.get("title", "Research Report")
        summary = report_data.get("summary", "")
        sections = report_data.get("sections", [])
        citations = report_data.get("citations", [])

        lines = [f"# {title}\n", f"**Executive Summary:**\n{summary}\n\n---\n"]

        for sec in sections:
            lines.append(f"## {sec.get('heading')}\n")
            lines.append(f"{sec.get('content')}\n")

        if citations:
            lines.append("## References\n")
            for c in citations:
                lines.append(f"[{c.get('number')}] [{c.get('title')}]({c.get('url')})")

        return "\n".join(lines)


report_service = ReportService()

"""
Evidence Collector and Parser for CARA.

Transforms raw tool outputs (search results, scraped pages, document snippets)
into validated, structured Evidence domain objects with credibility scores.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.interfaces.tool import ToolResult
from app.observability.logging import get_logger
from app.research.source_quality import classify_source_type, get_source_credibility
from app.schemas.evidence import Evidence, EvidenceStatus, SourceType

logger = get_logger(__name__)


class EvidenceCollector:
    """
    Normalizes raw tool outputs into structured Evidence items.
    """

    def extract_from_tool_result(
        self,
        tool_name: str,
        tool_result: ToolResult,
        default_claim: str = "Research context data",
    ) -> List[Evidence]:
        """
        Convert a ToolResult into a list of Evidence objects.
        """
        if not tool_result.success or not tool_result.data:
            return []

        evidence_list: List[Evidence] = []

        if tool_name == "web_search":
            for item in tool_result.data:
                url = item.get("url", "")
                snippet = item.get("snippet", "")
                title = item.get("title", "")
                if not url or not snippet:
                    continue

                ev = Evidence(
                    claim=title or default_claim,
                    content=snippet,
                    url=url,
                    title=title,
                    source_type=classify_source_type(url),
                    confidence=get_source_credibility(url),
                    status=EvidenceStatus.UNVERIFIED,
                )
                evidence_list.append(ev)

        elif tool_name == "url_reader":
            url = tool_result.metadata.get("url", "")
            content = tool_result.data
            if url and content:
                ev = Evidence(
                    claim=default_claim,
                    content=content[:3000],  # Keep relevant excerpt
                    url=url,
                    title="Web Document Content",
                    source_type=classify_source_type(url),
                    confidence=get_source_credibility(url),
                    status=EvidenceStatus.UNVERIFIED,
                )
                evidence_list.append(ev)

        elif tool_name == "github_search":
            for item in tool_result.data:
                url = item.get("url", "")
                name = item.get("name", "")
                desc = item.get("description", "")
                content = f"Repository: {name}\nStars: {item.get('stars', 0)}\nLanguage: {item.get('language')}\n{desc}"
                if url:
                    ev = Evidence(
                        claim=f"GitHub repository {name}",
                        content=content,
                        url=url,
                        title=name,
                        source_type=SourceType.GITHUB,
                        confidence=0.7,
                        status=EvidenceStatus.UNVERIFIED,
                    )
                    evidence_list.append(ev)

        elif tool_name == "document_search":
            for item in tool_result.data:
                fname = item.get("filename", "document")
                snippet = item.get("snippet", "")
                if snippet:
                    ev = Evidence(
                        claim=f"Local document: {fname}",
                        content=snippet,
                        url=f"local://data/documents/{fname}",
                        title=fname,
                        source_type=SourceType.OFFICIAL_DOCS,
                        confidence=0.95,
                        status=EvidenceStatus.UNVERIFIED,
                    )
                    evidence_list.append(ev)

        elif tool_name == "calculator":
            expr = tool_result.metadata.get("expression", "")
            val = tool_result.data
            ev = Evidence(
                claim=f"Calculation result: {expr} = {val}",
                content=f"Evaluated expression '{expr}' resulted in {val}",
                url="calculator://ast_evaluator",
                title="Calculator Execution",
                source_type=SourceType.OFFICIAL_DOCS,
                confidence=1.0,
                status=EvidenceStatus.VERIFIED,
            )
            evidence_list.append(ev)

        return evidence_list

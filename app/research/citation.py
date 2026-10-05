"""
Citation Mapping and Reference Formatter for CARA.

Links report assertions and claims back to evidence URLs, generating
clean Markdown reference lists and inline footnote markers ([1], [2]).
"""

from __future__ import annotations

from typing import Dict, List, Tuple
from app.schemas.evidence import Evidence
from app.schemas.report import Citation


class CitationMapper:
    """
    Manages citation indices and formats bibliographic links.
    """

    def __init__(self):
        self._url_to_index: Dict[str, int] = {}
        self._citations: List[Citation] = []

    def get_or_create_citation(self, evidence: Evidence) -> int:
        """
        Return the 1-based citation index for a piece of evidence.
        Re-uses indices for identical URLs.
        """
        url = evidence.url
        if url in self._url_to_index:
            return self._url_to_index[url]

        idx = len(self._citations) + 1
        self._url_to_index[url] = idx

        citation = Citation(
            number=idx,
            url=url,
            title=evidence.title or f"Source {idx}",
            source_type=evidence.source_type.value if hasattr(evidence.source_type, "value") else str(evidence.source_type),
        )
        self._citations.append(citation)
        return idx

    def get_citations(self) -> List[Citation]:
        """Return full list of registered citations."""
        return list(self._citations)

    def format_bibliography_markdown(self) -> str:
        """
        Format registered citations into standard Markdown references section.
        """
        if not self._citations:
            return "No citations available."

        lines = ["## References\n"]
        for cit in self._citations:
            lines.append(f"[{cit.number}] [{cit.title}]({cit.url}) *(Type: {cit.source_type})*")

        return "\n".join(lines)

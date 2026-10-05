"""
Evaluate Evidence Graph Node for CARA.

Applies source credibility scoring and sorts evidence prior to verification.
"""

from __future__ import annotations

from app.observability.logging import get_logger
from app.research.source_quality import classify_source_type, get_source_credibility
from app.schemas.research import ResearchState

logger = get_logger(__name__)


async def evaluate_evidence(state: ResearchState) -> ResearchState:
    """Enrich each evidence item with domain credibility scores."""
    for item in state.evidence_items:
        url = item.get("url", "")
        if url:
            item["source_type"] = classify_source_type(url).value
            item["confidence"] = get_source_credibility(url)

    # Sort descending by confidence
    state.evidence_items.sort(key=lambda x: x.get("confidence", 0.0), reverse=True)
    logger.info("Evidence evaluated and sorted", count=len(state.evidence_items))
    return state

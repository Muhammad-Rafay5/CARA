"""
Collect Evidence Graph Node for CARA.

Aggregates, normalizes, and de-duplicates evidence gathered during research executions.
"""

from __future__ import annotations

from app.observability.logging import get_logger
from app.schemas.research import ResearchState

logger = get_logger(__name__)


async def collect_evidence(state: ResearchState) -> ResearchState:
    """De-duplicate evidence items by source URL."""
    seen_urls = set()
    unique_items = []

    for item in state.evidence_items:
        url = item.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_items.append(item)
        elif not url:
            unique_items.append(item)

    state.evidence_items = unique_items
    logger.info("Evidence collected and de-duplicated", total_unique=len(unique_items))
    return state

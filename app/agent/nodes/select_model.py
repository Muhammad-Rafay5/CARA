"""
Select Model Graph Node for CARA.

Determines the optimal LLM profile deterministically without calling any LLM.
"""

from __future__ import annotations

from app.models.selector import ModelSelector
from app.observability.logging import get_logger
from app.schemas.research import ResearchComplexity, ResearchState

logger = get_logger(__name__)
selector = ModelSelector()


async def select_model(state: ResearchState) -> ResearchState:
    """Select the most suitable model profile for task complexity."""
    complexity = state.complexity or ResearchComplexity.MEDIUM
    chosen = selector.select(complexity=complexity)

    state.selected_provider = chosen.provider
    state.selected_model = chosen.model_name

    logger.info(
        "Model selected for research",
        provider=chosen.provider,
        model=chosen.model_name,
        tier=chosen.tier,
    )
    return state

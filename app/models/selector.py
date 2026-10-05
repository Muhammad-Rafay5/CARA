"""
Deterministic Model Selector for CARA.

Implements the multi-criteria weighted scoring engine for choosing the optimal
model given a research task's complexity, required context, budget, and constraints.

Scoring Formula:
    Score = (0.35 * Capability)
          + (0.15 * Context)
          + (0.15 * ToolUse)
          + (0.15 * Reliability)
          + (0.10 * Speed)
          + (0.10 * CostEfficiency)

Engineering Principles:
- Pure deterministic logic: same inputs + registry state always produce same output.
- No LLM call to decide which LLM to call (zero meta-prompt cost).
- Respects hard constraints: required context length, tool use capability, provider availability.
"""

from __future__ import annotations

from typing import Optional

from app.core.constants import (
    TIER_ADVANCED,
    TIER_FAST,
    TIER_STANDARD,
)
from app.core.exceptions import AllProvidersFailedError
from app.models.registry import ModelProfile, ModelRegistry, registry as default_registry
from app.observability.logging import get_logger
from app.schemas.research import ResearchComplexity

logger = get_logger(__name__)

# Scoring weights (must sum to 1.0)
WEIGHT_CAPABILITY = 0.35
WEIGHT_CONTEXT = 0.15
WEIGHT_TOOL_USE = 0.15
WEIGHT_RELIABILITY = 0.15
WEIGHT_SPEED = 0.10
WEIGHT_COST_EFFICIENCY = 0.10


def calculate_model_score(profile: ModelProfile) -> float:
    """
    Calculate the composite score for a model profile based on weighted metrics.
    """
    score = (
        WEIGHT_CAPABILITY * profile.capability_score
        + WEIGHT_CONTEXT * profile.context_score
        + WEIGHT_TOOL_USE * profile.tool_use_score
        + WEIGHT_RELIABILITY * profile.reliability_score
        + WEIGHT_SPEED * profile.speed_score
        + WEIGHT_COST_EFFICIENCY * profile.cost_efficiency_score
    )
    return round(score, 4)


class ModelSelector:
    """
    Deterministic selector for model execution.
    """

    def __init__(self, model_registry: Optional[ModelRegistry] = None):
        self.registry = model_registry or default_registry

    def _map_complexity_to_tier(self, complexity: ResearchComplexity) -> str:
        """
        Map research complexity to the preferred model tier.
        """
        if complexity == ResearchComplexity.SIMPLE:
            return TIER_FAST
        elif complexity == ResearchComplexity.MEDIUM:
            return TIER_STANDARD
        else:
            return TIER_ADVANCED

    def select(
        self,
        complexity: ResearchComplexity = ResearchComplexity.MEDIUM,
        min_context_tokens: int = 4000,
        requires_tools: bool = False,
        preferred_provider: Optional[str] = None,
    ) -> ModelProfile:
        """
        Select the best available model profile meeting all hard criteria.

        Args:
            complexity: Complexity of the research query.
            min_context_tokens: Minimum context window required.
            requires_tools: Whether native tool calling capability is needed.
            preferred_provider: Optional preferred provider filter.

        Returns:
            The highest scoring ModelProfile.

        Raises:
            AllProvidersFailedError: If no available model meets the hard constraints.
        """
        preferred_tier = self._map_complexity_to_tier(complexity)
        available_models = list(self.registry.available())

        if not available_models:
            logger.error("No models are currently marked available in registry")
            raise AllProvidersFailedError("No models are currently marked available in registry.")

        # Filter by hard constraints
        candidates = []
        for model in available_models:
            if model.context_tokens < min_context_tokens:
                continue
            if requires_tools and model.tool_use_score < 0.5:
                continue
            if preferred_provider and model.provider != preferred_provider:
                continue
            candidates.append(model)

        if not candidates:
            # Fallback relaxing preferred_provider if set
            if preferred_provider:
                logger.warning(
                    "No candidates found with preferred_provider, retrying without filter",
                    preferred_provider=preferred_provider,
                )
                return self.select(
                    complexity=complexity,
                    min_context_tokens=min_context_tokens,
                    requires_tools=requires_tools,
                    preferred_provider=None,
                )
            
            logger.error(
                "No candidate models satisfy constraints",
                complexity=complexity.value,
                min_context_tokens=min_context_tokens,
                requires_tools=requires_tools,
            )
            raise AllProvidersFailedError(
                f"No available model satisfies constraints: min_context={min_context_tokens}, requires_tools={requires_tools}"
            )

        # Score candidates with tier preference boost
        def candidate_key(m: ModelProfile) -> float:
            base_score = calculate_model_score(m)
            # Add bonus if model matches the target tier
            tier_bonus = 0.15 if m.tier == preferred_tier else 0.0
            return base_score + tier_bonus

        candidates.sort(key=candidate_key, reverse=True)
        chosen = candidates[0]

        logger.info(
            "Model selected deterministically",
            provider=chosen.provider,
            model=chosen.model_name,
            tier=chosen.tier,
            score=calculate_model_score(chosen),
        )
        return chosen

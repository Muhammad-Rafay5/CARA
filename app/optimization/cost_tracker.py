"""
Cost Tracker for CARA.

Calculates real-time financial costs for LLM invocations and tool usage:
- Free models (Groq open models, local Ollama, OpenRouter free tier): $0.00
- Paid models: exact price per 1k input/output tokens according to ModelProfile
"""

from __future__ import annotations

from typing import Dict, Optional
from app.models.registry import ModelProfile, registry as model_registry


class CostTracker:
    """
    Calculates exact dollar cost for prompt tokens and completion tokens.
    """

    def calculate_cost(
        self,
        provider: str,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """
        Calculate total cost in USD.
        """
        full_id = f"{provider}:{model_name}"
        profile = model_registry.get(full_id)

        if not profile:
            # If model profile is not registered, assume zero cost
            return 0.0

        input_cost = (prompt_tokens / 1000.0) * profile.cost_input_per_1k
        output_cost = (completion_tokens / 1000.0) * profile.cost_output_per_1k

        return round(input_cost + output_cost, 6)


cost_tracker = CostTracker()

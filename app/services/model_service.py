"""
Model Management Service for CARA.

Exposes operations to query available models, tiers, and provider statistics.
"""

from __future__ import annotations

from typing import Any, Dict, List
from app.models.registry import ModelProfile, registry as model_registry


class ModelService:
    """
    Exposes model catalog queries and operational status.
    """

    def list_models(self) -> List[Dict[str, Any]]:
        """Return list of all registered models and their profiles."""
        models = []
        for m in model_registry.all():
            models.append({
                "id": m.full_id,
                "provider": m.provider,
                "model_name": m.model_name,
                "tier": m.tier,
                "context_tokens": m.context_tokens,
                "output_tokens": m.output_tokens,
                "is_available": m.is_available,
                "cost_input_per_1k": m.cost_input_per_1k,
                "cost_output_per_1k": m.cost_output_per_1k,
            })
        return models

    def list_available_models(self) -> List[Dict[str, Any]]:
        """Return list of only currently active/available models."""
        return [m for m in self.list_models() if m["is_available"]]


model_service = ModelService()

"""
Model Cost metadata helpers for CARA.
"""

from app.models.registry import ModelProfile, registry as model_registry


def get_model_pricing(provider: str, model_name: str) -> dict:
    """Return dictionary with input and output pricing per 1k tokens."""
    full_id = f"{provider}:{model_name}"
    profile = model_registry.get(full_id)
    if not profile:
        return {"input_per_1k": 0.0, "output_per_1k": 0.0, "is_free": True}
    return {
        "input_per_1k": profile.cost_input_per_1k,
        "output_per_1k": profile.cost_output_per_1k,
        "is_free": (profile.cost_input_per_1k == 0.0 and profile.cost_output_per_1k == 0.0),
    }

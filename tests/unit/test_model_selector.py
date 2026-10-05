"""
Unit tests for ModelSelector and weighted scoring formula.
"""

import pytest
from app.models.registry import ModelProfile, ModelRegistry, registry
from app.models.selector import ModelSelector, calculate_model_score
from app.schemas.research import ResearchComplexity


def test_calculate_model_score():
    profile = ModelProfile(
        provider="test_prov",
        model_name="test_model",
        tier="standard",
        context_tokens=8192,
        output_tokens=4096,
        capability_score=0.8,
        context_score=0.7,
        tool_use_score=0.9,
        reliability_score=0.85,
        speed_score=0.6,
        cost_efficiency_score=0.9,
    )
    score = calculate_model_score(profile)
    assert 0.0 <= score <= 1.0
    assert score > 0.7


def test_model_selector_simple_complexity():
    selector = ModelSelector(registry)
    chosen = selector.select(complexity=ResearchComplexity.SIMPLE)
    assert chosen is not None
    assert chosen.is_available
    # Simple complexity should favor fast tier
    assert chosen.tier in ("fast", "standard")


def test_model_selector_complex_complexity():
    selector = ModelSelector(registry)
    chosen = selector.select(complexity=ResearchComplexity.COMPLEX)
    assert chosen is not None
    assert chosen.is_available

"""
Evaluation benchmark for Cost Efficiency: Naive vs Cost-Aware Agent.
"""

from app.models.registry import ModelProfile, registry as model_registry
from app.models.selector import ModelSelector
from app.optimization.cost_tracker import CostTracker
from app.schemas.research import ResearchComplexity


def test_cost_efficiency_comparison():
    """
    Demonstrate that deterministic model selection saves significant cost
    over a naive agent that always routes all simple tasks to an expensive advanced model.
    """
    tracker = CostTracker()
    selector = ModelSelector()

    # Query: Simple factual question
    simple_chosen = selector.select(complexity=ResearchComplexity.SIMPLE)

    # Calculate costs for 1,000 queries (4k prompt tokens, 1k completion tokens each)
    queries_count = 1000
    prompt_tokens_per_query = 4000
    comp_tokens_per_query = 1000

    cost_aware_cost_per_query = tracker.calculate_cost(
        simple_chosen.provider,
        simple_chosen.model_name,
        prompt_tokens_per_query,
        comp_tokens_per_query,
    )
    total_cost_aware = cost_aware_cost_per_query * queries_count

    # Naive agent cost (always using high-end commercial model, e.g. $0.015 / 1k tokens)
    naive_cost_per_query = (prompt_tokens_per_query / 1000.0) * 0.015 + (comp_tokens_per_query / 1000.0) * 0.060
    total_naive = naive_cost_per_query * queries_count

    # Savings calculation
    savings_pct = ((total_naive - total_cost_aware) / total_naive) * 100
    assert savings_pct > 50.0  # Demonstrates >50% cost reduction

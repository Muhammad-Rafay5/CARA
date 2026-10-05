"""
Unit tests for Cost Tracker and pricing logic.
"""

from app.optimization.cost_tracker import CostTracker


def test_cost_calculation():
    tracker = CostTracker()
    # Free tier or standard model cost calculations
    cost_free = tracker.calculate_cost("groq", "llama-3.1-8b-instant", 1000, 500)
    assert cost_free >= 0.0

    cost_gemini = tracker.calculate_cost("gemini", "gemini-1.5-flash", 10000, 2000)
    assert cost_gemini >= 0.0

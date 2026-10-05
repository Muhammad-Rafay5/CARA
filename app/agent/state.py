"""
Agent State representation for CARA.

Exports ResearchState and TypedDict equivalent for LangGraph node signatures.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict
from app.schemas.research import ResearchDepth, ResearchComplexity, ResearchStatus, ResearchState


class AgentStateDict(TypedDict, total=False):
    """
    TypedDict representation for LangGraph state passing.
    """
    request_id: str
    query: str
    depth: str
    status: str

    complexity: Optional[str]
    research_plan: List[str]
    current_step: int

    selected_model: Optional[str]
    selected_provider: Optional[str]

    tool_outputs: List[Dict[str, Any]]
    evidence_items: List[Dict[str, Any]]
    iteration: int

    verification_score: Optional[float]
    verification_status: Optional[str]
    unsupported_claims: List[str]

    report: Optional[str]
    summary: Optional[str]

    model_calls: int
    tool_calls: int
    tokens_used: int
    cost_usd: float
    warnings: List[str]

    max_iterations: int
    max_model_calls: int
    max_tool_calls: int
    max_tokens: int

    failure_history: List[Dict[str, Any]]
    last_error: Optional[str]


__all__ = ["ResearchState", "AgentStateDict"]

"""
Research Planner for CARA.

Classifies task complexity (SIMPLE, MEDIUM, COMPLEX) based on deterministic
query heuristics, decomposing queries into targeted research steps.
Respects depth setting (QUICK, STANDARD, DEEP) and budget limits.
"""

from __future__ import annotations

import re
from typing import List, Tuple

from app.schemas.research import ResearchComplexity, ResearchDepth, ResearchRequest
from app.observability.logging import get_logger

logger = get_logger(__name__)

# Keywords indicating complex comparative or multi-factor research
COMPLEX_INDICATORS = {
    "compare", "comparison", "vs", "versus", "architecture", "tradeoff",
    "trade-offs", "comprehensive", "in-depth", "benchmarks", "performance",
    "security analysis", "evaluation", "survey", "history and future",
}

# Keywords indicating simple factual or lookup queries
SIMPLE_INDICATORS = {
    "what is", "who is", "when did", "define", "definition", "meaning of",
    "calculate", "convert", "capital of", "release date", "latest version of",
}


class ResearchPlanner:
    """
    Analyzes research requests to produce a structured, bounded plan.
    """

    def analyze_complexity(self, query: str, depth: ResearchDepth) -> ResearchComplexity:
        """
        Classify complexity using deterministic heuristics.
        """
        if depth == ResearchDepth.QUICK:
            return ResearchComplexity.SIMPLE
        if depth == ResearchDepth.DEEP:
            return ResearchComplexity.COMPLEX

        q_lower = query.lower()
        word_count = len(query.split())

        # Check for explicit complex indicators
        for ind in COMPLEX_INDICATORS:
            if re.search(r"\b" + re.escape(ind) + r"\b", q_lower):
                return ResearchComplexity.COMPLEX

        # Check for simple indicators
        for ind in SIMPLE_INDICATORS:
            if q_lower.startswith(ind) and word_count <= 10:
                return ResearchComplexity.SIMPLE

        # Word count & question structure heuristic
        if word_count > 18 or (" and " in q_lower and " how " in q_lower):
            return ResearchComplexity.COMPLEX
        elif word_count < 8:
            return ResearchComplexity.SIMPLE
        else:
            return ResearchComplexity.MEDIUM

    def create_plan(self, query: str, complexity: ResearchComplexity) -> List[str]:
        """
        Generate sequence of research steps based on complexity.
        """
        if complexity == ResearchComplexity.SIMPLE:
            return [
                f"Identify direct factual answer for: '{query}'",
                "Extract verification source and summary",
            ]
        elif complexity == ResearchComplexity.MEDIUM:
            return [
                f"Gather foundational definitions and overview for: '{query}'",
                "Investigate key details, practical implications, and current standards",
                "Synthesize findings with authoritative citations",
            ]
        else:  # COMPLEX
            return [
                f"Map core concepts and identify comparative dimensions for: '{query}'",
                "Collect technical evidence across official documentation and benchmarks",
                "Cross-examine competing perspectives and identify potential contradictions",
                "Synthesize architectural trade-offs with structured citations and conclusions",
            ]

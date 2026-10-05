"""
Context Optimizer for CARA.

Prunes history, extracts concise snippets, and removes duplicate content
to stay comfortably within context windows and minimize prompt token costs.
"""

from __future__ import annotations

from typing import Any, Dict, List
from app.schemas.evidence import Evidence


class ContextOptimizer:
    """
    Optimizes context payload size sent to LLM calls.
    """

    def prune_evidence(
        self,
        evidence_list: List[Evidence],
        max_total_chars: int = 12000,
    ) -> List[Evidence]:
        """
        Sort by credibility and truncate total character length of evidence snippets.
        """
        if not evidence_list:
            return []

        # Sort descending by credibility
        sorted_ev = sorted(evidence_list, key=lambda e: e.confidence, reverse=True)
        pruned: List[Evidence] = []
        current_chars = 0

        for ev in sorted_ev:
            content_len = len(ev.content)
            if current_chars + content_len > max_total_chars:
                # Truncate this final evidence snippet
                remaining_space = max(200, max_total_chars - current_chars)
                truncated_ev = ev.model_copy(update={"content": ev.content[:remaining_space] + "... [truncated]"})
                pruned.append(truncated_ev)
                break
            pruned.append(ev)
            current_chars += content_len

        return pruned

    def format_evidence_for_prompt(self, evidence_list: List[Evidence]) -> str:
        """
        Format evidence into a concise numbered string for LLM prompts.
        """
        if not evidence_list:
            return "No evidence collected yet."

        blocks = []
        for i, ev in enumerate(evidence_list, 1):
            blocks.append(
                f"[{i}] SOURCE: {ev.title or 'Unknown'} ({ev.url})\n"
                f"CREDIBILITY: {ev.confidence:.2f}\n"
                f"CONTENT: {ev.content.strip()}\n"
            )

        return "\n".join(blocks)


context_optimizer = ContextOptimizer()

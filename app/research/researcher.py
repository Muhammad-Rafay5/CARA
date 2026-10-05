"""
Research Execution Coordinator for CARA.

Orchestrates iterative research execution:
- Dispatches tool calls (search, URL scraping, document reading, calculations).
- Enforces strict iteration limits (MAX_ITERATIONS = 3) and call limits (MAX_TOOL_CALLS = 20).
- Normalizes tool responses into structured Evidence objects via EvidenceCollector.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from app.core.exceptions import BudgetExceededError
from app.core.interfaces.tool import ToolResult
from app.observability.logging import get_logger
from app.research.evidence import EvidenceCollector
from app.schemas.evidence import Evidence
from app.schemas.research import ResearchComplexity, ResearchState
from app.tools.registry import ToolRegistry, tool_registry

logger = get_logger(__name__)


class Researcher:
    """
    Coordinates tool execution and evidence gathering for research tasks.
    """

    def __init__(
        self,
        tools: Optional[ToolRegistry] = None,
        collector: Optional[EvidenceCollector] = None,
    ):
        self.tools = tools or tool_registry
        self.collector = collector or EvidenceCollector()

    async def execute_step(
        self,
        query: str,
        step_description: str,
        state: ResearchState,
    ) -> List[Evidence]:
        """
        Execute research for a single plan step, checking guardrails before dispatching tools.
        """
        # Guardrail checks
        remaining_budget = state.max_tool_calls - state.tool_calls
        if remaining_budget <= 0:
            logger.warning("Tool call limit reached", current=state.tool_calls, max=state.max_tool_calls)
            state.warnings.append(f"Tool call limit ({state.max_tool_calls}) reached; stopping further tool calls.")
            return []

        gathered_evidence: List[Evidence] = []
        search_query = f"{query} {step_description}"[:100]

        # 1. Dispatch independent tools concurrently (web_search + document_search)
        tasks = [self.tools.execute("web_search", query=search_query, max_results=4)]
        task_types = ["web_search"]
        state.tool_calls += 1

        if state.tool_calls < state.max_tool_calls:
            tasks.append(self.tools.execute("document_search", query=query, max_results=2))
            task_types.append("document_search")
            state.tool_calls += 1

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for ttype, res in zip(task_types, results):
            if isinstance(res, Exception):
                logger.warning("Tool execution error", tool=ttype, error=str(res))
                continue
            if res.success and res.data:
                if ttype == "web_search":
                    state.tool_outputs.append({
                        "tool": "web_search",
                        "query": search_query,
                        "count": len(res.data),
                    })
                    new_ev = self.collector.extract_from_tool_result("web_search", res, default_claim=step_description)
                    gathered_evidence.extend(new_ev)
                elif ttype == "document_search":
                    doc_ev = self.collector.extract_from_tool_result("document_search", res)
                    gathered_evidence.extend(doc_ev)

        # 2. Pick top search result URL to read in detail if tool budget allows
        if state.tool_calls < state.max_tool_calls and gathered_evidence:
            for ev in gathered_evidence:
                top_url = ev.url
                if top_url and top_url.startswith("http"):
                    state.tool_calls += 1
                    url_res = await self.tools.execute("url_reader", url=top_url)
                    if url_res.success:
                        page_ev = self.collector.extract_from_tool_result("url_reader", url_res, default_claim=top_url)
                        gathered_evidence.extend(page_ev)
                    break

        logger.info(
            "Research step completed",
            step=step_description,
            evidence_count=len(gathered_evidence),
            total_tool_calls=state.tool_calls,
        )

        return gathered_evidence


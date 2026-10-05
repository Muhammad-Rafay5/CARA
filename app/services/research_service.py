"""
Research Service for CARA.

Coordinates request submission, invokes the LangGraph execution workflow,
maps state transitions to ResearchResponse schemas, and maintains in-memory results store.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Dict, Optional

from app.agent.graph import research_graph
from app.observability.logging import get_logger
from app.schemas.research import (
    ResearchDepth,
    ResearchRequest,
    ResearchResponse,
    ResearchState,
    ResearchStatus,
)

logger = get_logger(__name__)


class ResearchService:
    """
    Business logic layer for submitting and retrieving research tasks.
    """

    def __init__(self):
        self._results_store: Dict[str, ResearchResponse] = {}

    async def execute_research(self, request: ResearchRequest) -> ResearchResponse:
        """
        Execute research synchronously via the LangGraph state graph and return final response.
        """
        initial_state = ResearchState(
            query=request.query,
            depth=request.depth,
            max_tokens=request.max_tokens_override or 15000,
        )
        request_id = initial_state.request_id

        logger.info(
            "Submitting research task to LangGraph",
            request_id=request_id,
            query=request.query[:60],
            depth=request.depth.value,
        )

        try:
            # Execute compiled graph
            result_dict_or_state = await research_graph.ainvoke(initial_state)

            # Handle either dict or state object return
            if isinstance(result_dict_or_state, dict):
                final_state = ResearchState(**result_dict_or_state)
            else:
                final_state = result_dict_or_state

            response = ResearchResponse(
                request_id=final_state.request_id,
                status=final_state.status,
                report=final_state.report,
                summary=final_state.summary,
                verification_score=final_state.verification_score,
                total_tokens_used=final_state.tokens_used,
                total_model_calls=final_state.model_calls,
                total_tool_calls=final_state.tool_calls,
                total_cost_usd=final_state.cost_usd,
                iterations_completed=final_state.iteration,
                warnings=final_state.warnings,
                error=final_state.last_error,
                created_at=final_state.started_at,
                completed_at=final_state.completed_at,
            )

            self._results_store[request_id] = response
            return response

        except Exception as exc:
            logger.error("Failed to execute research graph", request_id=request_id, error=str(exc))
            err_response = ResearchResponse(
                request_id=request_id,
                status=ResearchStatus.FAILED,
                error=str(exc),
                warnings=["Research pipeline encountered an unrecoverable runtime exception."],
                created_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )
            self._results_store[request_id] = err_response
            return err_response

    def get_result(self, request_id: str) -> Optional[ResearchResponse]:
        """Retrieve previously executed research result."""
        return self._results_store.get(request_id)


research_service = ResearchService()

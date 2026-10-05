"""
Research routes for CARA.

POST /api/v1/research       — execute a research query via LangGraph agent
GET  /api/v1/research/{id}  — retrieve a result by request ID
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.errors import ErrorCode, ErrorResponse
from app.schemas.models import APIResponse
from app.schemas.research import ResearchRequest, ResearchResponse
from app.services.research_service import research_service

router = APIRouter(prefix="/api/v1", tags=["Research"])


@router.post(
    "/research",
    response_model=APIResponse[ResearchResponse],
    status_code=status.HTTP_200_OK,
    summary="Submit and execute a research query",
    description="Executes full autonomous multi-step research using LangGraph and verified citations.",
)
async def submit_research(
    request: ResearchRequest,
) -> APIResponse[ResearchResponse]:
    """Execute research task and return synthesized, verified report."""
    response = await research_service.execute_research(request)

    return APIResponse(
        success=(response.status.value != "failed"),
        data=response,
        message="Research execution completed.",
        request_id=response.request_id,
    )


@router.get(
    "/research/{request_id}",
    response_model=APIResponse[ResearchResponse],
    status_code=status.HTTP_200_OK,
    summary="Retrieve research result",
    description="Retrieve research output, status, and verification metrics by request ID.",
)
async def get_research_result(
    request_id: str,
) -> APIResponse[ResearchResponse]:
    """Retrieve previously executed research result."""
    result = research_service.get_result(request_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research request '{request_id}' not found.",
        )

    return APIResponse(
        success=True,
        data=result,
        message="Research result retrieved.",
        request_id=request_id,
    )

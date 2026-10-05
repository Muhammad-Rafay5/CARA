"""
Global error handler middleware for CARA.
Catches all unhandled exceptions and returns safe, structured error responses.

SECURITY: Never expose internal stack traces, file paths, or exception
messages directly to API consumers.
"""

from __future__ import annotations

import traceback
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.observability.logging import get_logger
from app.schemas.errors import ErrorCode, ErrorDetail, ErrorResponse

logger = get_logger(__name__)


async def global_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    FastAPI exception handler registered via app.add_exception_handler(Exception, ...).

    Converts any unhandled exception to a standardised ErrorResponse JSON payload.
    Logs the full traceback internally but returns only safe messages externally.
    """
    request_id: str = getattr(request.state, "request_id", str(uuid.uuid4()))

    # --- Handle Pydantic validation errors (400) ---
    if isinstance(exc, ValidationError):
        errors = [
            ErrorDetail(
                field=".".join(str(loc) for loc in e["loc"]) if e.get("loc") else None,
                message=e["msg"],
                code=ErrorCode.INVALID_REQUEST,
            )
            for e in exc.errors()
        ]
        logger.warning(
            "validation_error",
            request_id=request_id,
            path=request.url.path,
            error_count=len(errors),
        )
        body = ErrorResponse(
            message="Request validation failed.",
            error_code=ErrorCode.INVALID_REQUEST,
            errors=errors,
            request_id=request_id,
        )
        return JSONResponse(status_code=422, content=body.model_dump())

    # --- Handle all other exceptions (500) ---
    # Log FULL traceback internally for debugging
    logger.error(
        "unhandled_exception",
        request_id=request_id,
        path=request.url.path,
        exc_type=type(exc).__name__,
        traceback=traceback.format_exc(),
    )

    # Return SAFE external response — no internals exposed
    body = ErrorResponse(
        message="An internal error occurred. Please try again or contact support.",
        error_code=ErrorCode.INTERNAL_ERROR,
        request_id=request_id,
    )
    return JSONResponse(status_code=500, content=body.model_dump())

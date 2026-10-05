"""
Request ID middleware for CARA.
Assigns a unique UUID to every incoming request and propagates it via
the X-Request-ID response header and request.state.request_id.
"""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

import structlog

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that:
    1. Reads X-Request-ID from the incoming request (if provided by caller).
    2. Generates a fresh UUID4 if none is provided.
    3. Binds the request_id to structlog's context variables for this request.
    4. Injects X-Request-ID into the outgoing response headers.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Honour caller-provided request ID or generate one
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())

        # Attach to request state for downstream handlers
        request.state.request_id = request_id

        # Bind to structlog context so all log lines in this request carry it
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response: Response = await call_next(request)

        # Propagate back to caller
        response.headers[REQUEST_ID_HEADER] = request_id

        return response

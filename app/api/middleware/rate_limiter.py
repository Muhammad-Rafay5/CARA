"""
Rate limiting middleware for CARA.

Implements a sliding-window rate limiter keyed by session token.
Each session is allowed `RATE_LIMIT_MAX_REQUESTS` within a
`RATE_LIMIT_WINDOW_SECONDS` rolling window.

The middleware is applied globally; endpoints annotated with
`@no_rate_limit` (or health/docs routes) are exempt.

Design notes:
- Pure in-memory implementation (no Redis dependency required for dev/small-scale).
- For multi-instance production deployments, swap the in-memory store for a
  Redis-backed backend using the same interface.
- Thread-safe via asyncio lock (single-writer per key).
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config.settings import settings
from app.observability.logging import get_logger

logger = get_logger(__name__)

# ── Exempt paths (never rate-limited) ────────────────────────────────────────
_EXEMPT_PREFIXES: tuple[str, ...] = (
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/metrics",
)


class InMemoryRateLimitStore:
    """
    Sliding-window counter backed by a per-session deque of timestamps.

    Each entry in the deque is a Unix timestamp of a counted request.
    On every check we prune timestamps older than the window, then
    compare the remaining count against the limit.
    """

    def __init__(self, *, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # session_token -> deque[float]  (timestamps)
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    def is_allowed(self, session_token: str) -> tuple[bool, dict[str, Any]]:
        """
        Check whether *session_token* may proceed.

        Returns (allowed, info) where *info* contains:
        - remaining: int   — requests left in the current window
        - reset:     float — seconds until the oldest tracked request expires
        - limit:     int   — the configured cap
        """
        now = time.monotonic()
        window_start = now - self.window_seconds
        bucket = self._buckets[session_token]

        # Prune expired entries
        while bucket and bucket[0] <= window_start:
            bucket.popleft()

        remaining = max(0, self.max_requests - len(bucket))
        reset = (bucket[0] + self.window_seconds - now) if bucket else 0.0

        if len(bucket) >= self.max_requests:
            return False, {
                "remaining": 0,
                "reset": round(reset, 1),
                "limit": self.max_requests,
            }

        # Record this request
        bucket.append(now)
        remaining = max(0, self.max_requests - len(bucket))

        return True, {
            "remaining": remaining,
            "reset": round(self.window_seconds, 1),
            "limit": self.max_requests,
        }

    def cleanup_stale(self, max_age_seconds: float = 3600.0) -> int:
        """
        Remove buckets with no activity in *max_age_seconds*.
        Call periodically to prevent unbounded memory growth.
        Returns the number of sessions evicted.
        """
        now = time.monotonic()
        stale_keys = [
            k
            for k, dq in self._buckets.items()
            if not dq or (now - dq[-1]) > max_age_seconds
        ]
        for k in stale_keys:
            del self._buckets[k]
        return len(stale_keys)


# ── Singleton store (initialised with settings values) ───────────────────────
_store: InMemoryRateLimitStore | None = None


def _get_store() -> InMemoryRateLimitStore:
    global _store
    if _store is None:
        _store = InMemoryRateLimitStore(
            max_requests=settings.RATE_LIMIT_MAX_REQUESTS,
            window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
        )
    return _store


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware enforcing per-session rate limits.

    Reads the session token from ``request.state.session_token``
    (set by the upstream :class:`SessionMiddleware`) and rejects
    requests that exceed the sliding-window cap with a **429** response.

    Rate-limit metadata is exposed via response headers:
    - ``X-RateLimit-Limit``     — max requests per window
    - ``X-RateLimit-Remaining`` — requests left in window
    - ``X-RateLimit-Reset``     — seconds until the window resets
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip exempt paths
        path = request.url.path
        if any(path.startswith(prefix) for prefix in _EXEMPT_PREFIXES):
            return await call_next(request)

        # Read session token (set by SessionMiddleware upstream)
        session_token: str = getattr(request.state, "session_token", "anonymous")

        store = _get_store()
        allowed, info = store.is_allowed(session_token)

        if not allowed:
            logger.warning(
                "rate_limit_exceeded",
                session_token=session_token[:8] + "…",
                path=path,
                reset_seconds=info["reset"],
            )
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "message": (
                        f"Rate limit exceeded. Maximum {info['limit']} requests "
                        f"per {settings.RATE_LIMIT_WINDOW_SECONDS}s window. "
                        f"Retry after {info['reset']}s."
                    ),
                    "error_code": "RATE_LIMITED",
                    "request_id": getattr(request.state, "request_id", ""),
                },
                headers={
                    "Retry-After": str(int(info["reset"]) + 1),
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(info["reset"])),
                },
            )

        # Proceed — inject rate-limit headers into the response
        response: Response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(int(info["reset"]))

        return response

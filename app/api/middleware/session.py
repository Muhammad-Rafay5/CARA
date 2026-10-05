"""
Session token middleware for CARA.

Issues and validates stateless, HMAC-signed session tokens so the
rate limiter (and future per-user features) can identify callers
without requiring user accounts.

Token lifecycle
───────────────
1. Client sends `X-Session-Token` header on every request.
2. If absent or invalid, the middleware mints a fresh token and returns
   it in the `X-Session-Token` response header.
3. Tokens are **stateless** — signed with the app SECRET_KEY — so the
   server does not need a session store.
4. Tokens expire after `SESSION_TOKEN_TTL_HOURS` hours.  Once expired
   the server transparently issues a new one.

Token format:  ``<base64url(payload)>.<base64url(signature)>``
Payload:       ``{"sid": "<uuid4>", "iat": <unix_timestamp>}``
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.config.settings import settings
from app.observability.logging import get_logger

logger = get_logger(__name__)

SESSION_HEADER = "X-Session-Token"


# ── Token helpers ────────────────────────────────────────────────────────────

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    # Re-add removed padding
    s += "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s)


def _sign(payload_b64: str, secret: str) -> str:
    """HMAC-SHA256 signature over the payload segment."""
    sig = hmac.new(
        secret.encode(), payload_b64.encode(), hashlib.sha256
    ).digest()
    return _b64url_encode(sig)


def create_session_token(secret: str) -> str:
    """Mint a new signed session token."""
    payload = json.dumps(
        {"sid": str(uuid.uuid4()), "iat": int(time.time())},
        separators=(",", ":"),
    ).encode()
    payload_b64 = _b64url_encode(payload)
    signature = _sign(payload_b64, secret)
    return f"{payload_b64}.{signature}"


def validate_session_token(token: str, secret: str) -> str | None:
    """
    Validate a session token's signature and expiry.

    Returns the session ID (``sid``) if valid, ``None`` otherwise.
    """
    parts = token.split(".")
    if len(parts) != 2:
        return None

    payload_b64, sig_b64 = parts
    expected_sig = _sign(payload_b64, secret)

    if not hmac.compare_digest(sig_b64, expected_sig):
        return None

    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except (json.JSONDecodeError, Exception):
        return None

    # Check expiry
    iat = payload.get("iat", 0)
    ttl_seconds = settings.SESSION_TOKEN_TTL_HOURS * 3600
    if time.time() - iat > ttl_seconds:
        return None

    return payload.get("sid")


# ── Middleware ───────────────────────────────────────────────────────────────

class SessionMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware that assigns a session identity to every request.

    Reads `X-Session-Token` from the incoming request.  If the token is
    missing, invalid, or expired, a new token is minted and returned in the
    response `X-Session-Token` header.

    The resolved session ID is stored at ``request.state.session_token``
    for downstream middleware (rate limiter) and route handlers.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        secret = settings.SECRET_KEY
        raw_token = request.headers.get(SESSION_HEADER)
        new_token: str | None = None

        if raw_token:
            sid = validate_session_token(raw_token, secret)
            if sid:
                # Valid token — use existing session id
                request.state.session_token = sid
            else:
                # Invalid / expired — issue fresh token
                new_token = create_session_token(secret)
                sid = validate_session_token(new_token, secret)
                request.state.session_token = sid or str(uuid.uuid4())
        else:
            # No token supplied — mint a new one
            new_token = create_session_token(secret)
            sid = validate_session_token(new_token, secret)
            request.state.session_token = sid or str(uuid.uuid4())

        response: Response = await call_next(request)

        # Always send the token back (new or echo the valid one)
        response.headers[SESSION_HEADER] = new_token or raw_token or ""

        return response

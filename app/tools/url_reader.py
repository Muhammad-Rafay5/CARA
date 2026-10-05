"""
SSRF-Safe URL Reader Tool for CARA.

Fetches webpage content with strict security guardrails:
- SSRF blocklist: localhost, private IP ranges (127.0.0.0/8, 10.0.0.0/8, 192.168.0.0/16, 172.16.0.0/12), AWS metadata (169.254.169.254), IPv6 loopback (::1)
- Scheme validation: Only http:// and https:// allowed
- Timeouts: Configurable timeout (default 15s)
- Byte limit: Truncation at 1MB to prevent memory exhaustion
- Text extraction: Strips scripts, styling, and extracts readable text
"""

from __future__ import annotations

import asyncio
import ipaddress
import re
from typing import Any, List, Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.config.settings import settings
from app.core.constants import (
    DEFAULT_HTTP_TIMEOUT_SECONDS,
    DEFAULT_MAX_RESPONSE_BYTES,
    SSRF_BLOCKED_PREFIXES,
)
from app.core.exceptions import SSRFBlockedError
from app.core.interfaces.tool import ToolParameter, ToolResult
from app.observability.logging import get_logger
from app.optimization.cache import research_cache
from app.tools.base import BaseTool

logger = get_logger(__name__)

# Shared keep-alive client to prevent TCP/TLS connection churn
_shared_client: Optional[httpx.AsyncClient] = None


def get_shared_client(timeout: int = DEFAULT_HTTP_TIMEOUT_SECONDS) -> httpx.AsyncClient:
    """Provide a singleton httpx.AsyncClient with connection pooling and keep-alive."""
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            max_redirects=3,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        )
    return _shared_client


def _parse_and_clean_html(content_bytes: bytes, content_type: str, max_bytes: int) -> str:
    """CPU-bound HTML extraction offloaded to worker thread to prevent event-loop blocking."""
    if "html" in content_type:
        soup = BeautifulSoup(content_bytes[:max_bytes], "html.parser")
        for script in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            script.decompose()
        text = soup.get_text(separator="\n")
    else:
        text = content_bytes[:max_bytes].decode("utf-8", errors="replace")

    clean_lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(clean_lines)[:10000]


def validate_target_url(url: str) -> None:
    """
    Ensure the target URL does not violate SSRF constraints or point to private IP spaces.
    Raises SSRFBlockedError if unsafe.
    """
    url_lower = url.lower().strip()

    # 1. Check scheme
    if not (url_lower.startswith("http://") or url_lower.startswith("https://")):
        raise SSRFBlockedError(url)

    # 2. Check blocked prefix substrings
    for prefix in SSRF_BLOCKED_PREFIXES:
        if url_lower.startswith(prefix.lower()):
            raise SSRFBlockedError(url)

    # 3. Parse host and check for private/loopback/link-local IP addresses
    parsed = urlparse(url)
    hostname = parsed.hostname

    if not hostname:
        raise SSRFBlockedError(url)

    if hostname in {"localhost", "127.0.0.1", "::1", "0.0.0.0"}:
        raise SSRFBlockedError(url)

    # Check if hostname is an IP address
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise SSRFBlockedError(url)
    except ValueError:
        # Not a raw IP literal (domain name); will be resolved via DNS
        pass


class URLReaderTool(BaseTool):
    """
    SSRF-protected web document fetcher and text extractor.
    """

    def __init__(
        self,
        timeout: int = DEFAULT_HTTP_TIMEOUT_SECONDS,
        max_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    ):
        self.timeout = timeout
        self.max_bytes = max_bytes

    @property
    def name(self) -> str:
        return "url_reader"

    @property
    def description(self) -> str:
        return (
            "Fetch and extract clean readable text from a public web URL. "
            "Enforces SSRF prevention (blocks private/internal IPs) and size limits (1MB)."
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="url",
                type="string",
                description="The public web URL to fetch (must start with http:// or https://).",
                required=True,
            )
        ]

    async def execute(self, **kwargs: Any) -> ToolResult:
        url = kwargs.get("url", "").strip()
        if not url:
            return ToolResult.fail("Missing target URL.")

        try:
            validate_target_url(url)
        except SSRFBlockedError as err:
            logger.warning("SSRF blocked URL attempt", url=url, reason=str(err))
            return ToolResult.fail(f"Access to URL blocked by SSRF security policy: {str(err)}")

        # Check in-memory tool cache to avoid redundant network fetch
        cache_key = f"url:{url}"
        cached = research_cache.get(cache_key)
        if cached:
            logger.debug("URL reader cache hit", url=url)
            return ToolResult.ok(
                data=cached["data"],
                url=cached["url"],
                byte_length=cached["byte_length"],
                truncated=cached["truncated"],
            )

        headers = {
            "User-Agent": "CARA-Research-Agent/1.0 (+https://github.com/cara-research)",
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9",
        }

        try:
            client = get_shared_client(self.timeout)
            response = await client.get(url, headers=headers)

            # Check post-redirect URL for SSRF as well
            final_url = str(response.url)
            validate_target_url(final_url)

            if response.status_code >= 400:
                return ToolResult.fail(
                    f"HTTP request failed with status {response.status_code}",
                    status_code=response.status_code,
                    url=url,
                )

            content_bytes = response.content[: self.max_bytes]
            content_type = response.headers.get("content-type", "").lower()

            # Offload CPU-bound HTML extraction to thread to avoid freezing async event loop
            cleaned_text = await asyncio.to_thread(
                _parse_and_clean_html,
                content_bytes,
                content_type,
                self.max_bytes,
            )

            result_meta = {
                "data": cleaned_text,
                "url": final_url,
                "byte_length": len(content_bytes),
                "truncated": len(response.content) > self.max_bytes,
            }
            # Cache URL content for 30 minutes
            research_cache.set(cache_key, result_meta, ttl=1800.0)

            return ToolResult.ok(**result_meta)

        except httpx.TimeoutException:
            return ToolResult.fail(f"Request to '{url}' timed out after {self.timeout}s.")
        except httpx.RequestError as exc:
            return ToolResult.fail(f"Network error accessing '{url}': {str(exc)}")
        except Exception as exc:
            return ToolResult.fail(f"Failed to fetch or parse URL '{url}': {str(exc)}")


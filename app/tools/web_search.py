"""
Web Search Tool for CARA.

Integrates with DuckDuckGo Search (HTML/lite or DDGS) to retrieve relevant
web search results (titles, snippets, URLs) without requiring paid API keys.
Gracefully handles rate limits and network errors with caching and connection pooling.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, quote_plus, urlparse

import httpx
from bs4 import BeautifulSoup

from app.core.constants import DEFAULT_HTTP_TIMEOUT_SECONDS
from app.core.interfaces.tool import ToolParameter, ToolResult
from app.observability.logging import get_logger
from app.optimization.cache import research_cache
from app.tools.base import BaseTool

logger = get_logger(__name__)

# Shared keep-alive client to prevent TCP/TLS connection churn
_shared_search_client: Optional[httpx.AsyncClient] = None


def get_search_client(timeout: int = DEFAULT_HTTP_TIMEOUT_SECONDS) -> httpx.AsyncClient:
    """Provide a singleton httpx.AsyncClient for search requests with connection pooling."""
    global _shared_search_client
    if _shared_search_client is None or _shared_search_client.is_closed:
        _shared_search_client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=15, max_connections=30),
        )
    return _shared_search_client


def _parse_ddg_results(html_text: str, max_results: int) -> List[Dict[str, str]]:
    """CPU-bound HTML DOM extraction offloaded to worker thread to prevent event-loop blocking."""
    soup = BeautifulSoup(html_text, "html.parser")
    results: List[Dict[str, str]] = []

    result_elements = soup.find_all("div", class_="result")
    for el in result_elements:
        title_elem = el.find("a", class_="result__a")
        snippet_elem = el.find("a", class_="result__snippet")

        if title_elem:
            title = title_elem.get_text(strip=True)
            raw_href = title_elem.get("href", "")
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

            # DuckDuckGo wraps links in uddg redirect URLs; extract if present
            if "uddg=" in raw_href:
                parsed_qs = parse_qs(urlparse(raw_href).query)
                dest_url = parsed_qs.get("uddg", [raw_href])[0]
            else:
                dest_url = raw_href

            if dest_url.startswith("http"):
                results.append({
                    "title": title,
                    "snippet": snippet,
                    "url": dest_url,
                })

        if len(results) >= max_results:
            break

    return results


class WebSearchTool(BaseTool):
    """
    Retrieves web search results using DuckDuckGo HTML search.
    """

    def __init__(self, timeout: int = DEFAULT_HTTP_TIMEOUT_SECONDS):
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "Search the public internet for articles, documentation, facts, and news. "
            "Returns top search result titles, summaries/snippets, and destination URLs."
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="The search query terms or question.",
                required=True,
            ),
            ToolParameter(
                name="max_results",
                type="integer",
                description="Maximum number of search results to retrieve (default 5, max 10).",
                required=False,
                default=5,
            ),
        ]

    async def execute(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query", "").strip()
        max_results = min(int(kwargs.get("max_results", 5)), 10)

        if not query:
            return ToolResult.fail("Search query cannot be empty.")

        # Check in-memory search cache to eliminate duplicate network traffic
        cache_key = f"search:{query}:{max_results}"
        cached_results = research_cache.get(cache_key)
        if cached_results is not None:
            logger.debug("Web search cache hit", query=query)
            return ToolResult.ok(
                data=cached_results,
                query=query,
                result_count=len(cached_results),
            )

        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        try:
            client = get_search_client(self.timeout)
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                return ToolResult.fail(
                    f"Search engine responded with HTTP status {response.status_code}",
                    query=query,
                )

            # Offload HTML parsing to thread
            results = await asyncio.to_thread(_parse_ddg_results, response.text, max_results)

            if results:
                research_cache.set(cache_key, results, ttl=1800.0)

            logger.info("Web search completed", query=query, result_count=len(results))
            return ToolResult.ok(
                data=results,
                query=query,
                result_count=len(results),
            )

        except httpx.TimeoutException:
            return ToolResult.fail(f"Search request timed out after {self.timeout}s.")
        except Exception as exc:
            return ToolResult.fail(f"Web search error: {str(exc)}")


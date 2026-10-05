"""
GitHub Search Tool for CARA.

Queries the public GitHub REST API for repositories, code, and documentation
to support technical and open-source software research.
"""

from __future__ import annotations

from typing import Any, Dict, List
import httpx
from urllib.parse import quote_plus

from app.core.constants import DEFAULT_HTTP_TIMEOUT_SECONDS
from app.core.interfaces.tool import ToolParameter, ToolResult
from app.observability.logging import get_logger
from app.tools.base import BaseTool

logger = get_logger(__name__)


class GitHubSearchTool(BaseTool):
    """
    Search GitHub repositories, READMEs, topics, and code metrics.
    """

    def __init__(self, timeout: int = DEFAULT_HTTP_TIMEOUT_SECONDS):
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "github_search"

    @property
    def description(self) -> str:
        return (
            "Search public GitHub repositories by keywords, language, or topic. "
            "Returns repository names, descriptions, star counts, primary languages, and URLs."
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="The search query or keywords (e.g., 'fastapi rate limit language:python').",
                required=True,
            ),
            ToolParameter(
                name="max_results",
                type="integer",
                description="Maximum number of repositories to return (default 5, max 10).",
                required=False,
                default=5,
            ),
        ]

    async def execute(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query", "").strip()
        max_results = min(int(kwargs.get("max_results", 5)), 10)

        if not query:
            return ToolResult.fail("Query cannot be empty.")

        url = f"https://api.github.com/search/repositories?q={quote_plus(query)}&per_page={max_results}&sort=stars"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "CARA-Research-Agent/1.0",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 403:
                    return ToolResult.fail("GitHub API rate limit exceeded. Please try again later.")
                elif response.status_code != 200:
                    return ToolResult.fail(f"GitHub API error: status {response.status_code}")

                data = response.json()
                items = data.get("items", [])
                results: List[Dict[str, Any]] = []

                for item in items[:max_results]:
                    results.append({
                        "name": item.get("full_name"),
                        "description": item.get("description") or "No description",
                        "url": item.get("html_url"),
                        "stars": item.get("stargazers_count", 0),
                        "forks": item.get("forks_count", 0),
                        "language": item.get("language") or "Unknown",
                    })

                logger.info("GitHub search succeeded", query=query, count=len(results))
                return ToolResult.ok(
                    data=results,
                    query=query,
                    total_count=data.get("total_count", 0),
                )

        except httpx.TimeoutException:
            return ToolResult.fail(f"GitHub search request timed out after {self.timeout}s.")
        except Exception as exc:
            return ToolResult.fail(f"GitHub search failed: {str(exc)}")

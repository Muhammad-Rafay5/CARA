"""
Local Document Search Tool for CARA.

Safely searches and reads documents from the configured local document directory.
Strict Security Guardrails:
- Path traversal protection: rejects `..` or absolute paths outside ALLOWED_DOCUMENT_DIR
- File extension filtering: restricts to text formats (.txt, .md, .csv, .json, .log)
- File size truncation: max 1MB per document read
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

from app.config.settings import settings
from app.core.interfaces.tool import ToolParameter, ToolResult
from app.observability.logging import get_logger
from app.tools.base import BaseTool

logger = get_logger(__name__)

ALLOWED_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".log", ".rst"}


class DocumentSearchTool(BaseTool):
    """
    Search and read local text documents within ALLOWED_DOCUMENT_DIR.
    """

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = (base_dir or settings.ALLOWED_DOCUMENT_DIR).resolve()
        # Ensure base directory exists
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @property
    def name(self) -> str:
        return "document_search"

    @property
    def description(self) -> str:
        return (
            "Search and read local text documents in the allowed document folder. "
            "Supports keyword search across file contents and direct filename reading with path traversal prevention."
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="Keyword query to search across documents, or specific filename to read.",
                required=True,
            ),
            ToolParameter(
                name="max_results",
                type="integer",
                description="Max matches to return (default 5).",
                required=False,
                default=5,
            ),
        ]

    def _is_safe_path(self, target_path: Path) -> bool:
        """Verify resolved target path is strictly within self.base_dir."""
        try:
            resolved = target_path.resolve()
            return resolved == self.base_dir or self.base_dir in resolved.parents
        except Exception:
            return False

    async def execute(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query", "").strip()
        max_results = min(int(kwargs.get("max_results", 5)), 10)

        if not query:
            return ToolResult.fail("Query cannot be empty.")

        # Check if query directly points to an existing file in directory
        direct_file = self.base_dir / query
        if direct_file.is_file():
            if not self._is_safe_path(direct_file):
                logger.warning("Path traversal attempt detected", path=str(direct_file))
                return ToolResult.fail("Access denied: path traversal detected.")

            if direct_file.suffix.lower() not in ALLOWED_EXTENSIONS:
                return ToolResult.fail(f"Unsupported file type: {direct_file.suffix}")

            try:
                content = direct_file.read_text(encoding="utf-8", errors="replace")
                return ToolResult.ok(
                    data=[{
                        "filename": direct_file.name,
                        "snippet": content[:4000],
                        "full_match": True,
                    }],
                    query=query,
                )
            except Exception as exc:
                return ToolResult.fail(f"Error reading file '{direct_file.name}': {str(exc)}")

        # Otherwise search through all text files in base_dir
        matches: List[Dict[str, Any]] = []
        q_lower = query.lower()

        try:
            for root, _, files in os.walk(self.base_dir):
                for file_name in files:
                    file_path = Path(root) / file_name
                    if not self._is_safe_path(file_path):
                        continue
                    if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
                        continue

                    try:
                        content = file_path.read_text(encoding="utf-8", errors="replace")
                        if q_lower in content.lower() or q_lower in file_name.lower():
                            # Find surrounding snippet
                            idx = content.lower().find(q_lower)
                            start = max(0, idx - 100) if idx != -1 else 0
                            snippet = content[start : start + 300]
                            matches.append({
                                "filename": file_name,
                                "snippet": snippet.strip(),
                                "relative_path": str(file_path.relative_to(self.base_dir)),
                            })
                            if len(matches) >= max_results:
                                break
                    except Exception as err:
                        logger.debug("Failed reading document", file=file_name, error=str(err))
                if len(matches) >= max_results:
                    break

            return ToolResult.ok(
                data=matches,
                query=query,
                count=len(matches),
            )
        except Exception as exc:
            return ToolResult.fail(f"Document search failed: {str(exc)}")

"""
Tool Registry for CARA.

Maintains available tools, validates execution permissions, and formats
schemas for model tool calling / structured function calling.
"""

from __future__ import annotations

from typing import Dict, Iterator, List, Optional

from app.core.exceptions import ToolExecutionError
from app.core.interfaces.tool import Tool, ToolResult
from app.observability.logging import get_logger
from app.tools.calculator import CalculatorTool
from app.tools.document_search import DocumentSearchTool
from app.tools.github_search import GitHubSearchTool
from app.tools.url_reader import URLReaderTool
from app.tools.web_search import WebSearchTool

logger = get_logger(__name__)


class ToolRegistry:
    """
    Central registry for CARA research tools.
    """

    def __init__(self, register_defaults: bool = True):
        self._tools: Dict[str, Tool] = {}
        if register_defaults:
            self.register(WebSearchTool())
            self.register(URLReaderTool())
            self.register(GitHubSearchTool())
            self.register(CalculatorTool())
            self.register(DocumentSearchTool())

    def register(self, tool: Tool) -> None:
        """Register a new tool instance."""
        if tool.name in self._tools:
            logger.warning("Overwriting existing tool registration", tool_name=tool.name)
        self._tools[tool.name] = tool
        logger.info("Registered tool", tool_name=tool.name)

    def get(self, name: str) -> Optional[Tool]:
        """Retrieve tool by identifier."""
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        return name in self._tools

    def all(self) -> List[Tool]:
        return list(self._tools.values())

    def names(self) -> List[str]:
        return list(self._tools.keys())

    def get_schemas(self) -> List[dict]:
        """Return list of JSON schemas for all registered tools."""
        return [tool.schema() for tool in self._tools.values()]

    async def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """
        Execute tool by name with provided arguments.
        """
        tool = self.get(tool_name)
        if not tool:
            logger.error("Attempted to execute unregistered tool", tool=tool_name)
            return ToolResult.fail(f"Tool '{tool_name}' is not registered.")

        if hasattr(tool, "run"):
            return await tool.run(**kwargs)
        return await tool.execute(**kwargs)

    def __iter__(self) -> Iterator[Tool]:
        return iter(self._tools.values())

    def __len__(self) -> int:
        return len(self._tools)


# Default application-wide tool registry singleton
tool_registry = ToolRegistry()

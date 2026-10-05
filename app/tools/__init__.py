"""
Tools subsystem for CARA.

Exports:
- BaseTool
- ToolRegistry & default singleton tool_registry
- WebSearchTool
- URLReaderTool
- GitHubSearchTool
- CalculatorTool
- DocumentSearchTool
"""

from app.tools.base import BaseTool
from app.tools.calculator import CalculatorTool
from app.tools.document_search import DocumentSearchTool
from app.tools.github_search import GitHubSearchTool
from app.tools.registry import ToolRegistry, tool_registry
from app.tools.url_reader import URLReaderTool
from app.tools.web_search import WebSearchTool

__all__ = [
    "BaseTool",
    "CalculatorTool",
    "DocumentSearchTool",
    "GitHubSearchTool",
    "ToolRegistry",
    "URLReaderTool",
    "WebSearchTool",
    "tool_registry",
]

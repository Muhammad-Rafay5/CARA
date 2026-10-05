"""Core interfaces package for CARA."""

from app.core.interfaces.cache import CacheRepository
from app.core.interfaces.model import (
    ModelCapabilities,
    ModelMessage,
    ModelProvider,
    ModelResponse,
)
from app.core.interfaces.storage import StorageRepository
from app.core.interfaces.tool import Tool, ToolParameter, ToolResult

__all__ = [
    "CacheRepository",
    "ModelCapabilities",
    "ModelMessage",
    "ModelProvider",
    "ModelResponse",
    "StorageRepository",
    "Tool",
    "ToolParameter",
    "ToolResult",
]

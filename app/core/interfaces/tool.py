"""
Abstract Tool Interface for CARA.
All tool implementations must conform to this contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolParameter:
    """Describes a single parameter accepted by a tool."""

    name: str
    type: str  # "string" | "integer" | "float" | "boolean"
    description: str
    required: bool = True
    default: Any = None


@dataclass
class ToolResult:
    """Standardized output returned by any tool execution."""

    success: bool
    data: Any  # raw tool output
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, data: Any, **metadata: Any) -> "ToolResult":
        return cls(success=True, data=data, metadata=metadata)

    @classmethod
    def fail(cls, error: str, **metadata: Any) -> "ToolResult":
        return cls(success=False, data=None, error=error, metadata=metadata)


class Tool(ABC):
    """
    Abstract base class for all research tools.

    Security contract:
    - Tools MUST validate all inputs before execution.
    - Tools MUST NOT execute arbitrary code (no eval/exec).
    - Tools MUST enforce timeouts internally or rely on caller timeouts.
    - URL-fetching tools MUST enforce SSRF blocklists.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier used in the registry (e.g., 'web_search')."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what the tool does."""

    @property
    @abstractmethod
    def parameters(self) -> list[ToolParameter]:
        """
        Ordered list of parameters this tool accepts.
        Used for schema validation before execution.
        """

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        Execute the tool with provided arguments.

        Callers must validate kwargs against self.parameters before calling.

        Returns:
            ToolResult with success flag, data, and optional error.

        Raises:
            ToolExecutionError: For unrecoverable tool failures.
        """

    def validate_inputs(self, kwargs: dict[str, Any]) -> list[str]:
        """
        Validate provided kwargs against parameter schema.

        Returns:
            List of validation error messages. Empty list = valid.
        """
        errors: list[str] = []
        for param in self.parameters:
            if param.required and param.name not in kwargs:
                errors.append(f"Missing required parameter: '{param.name}'")
            elif param.name in kwargs:
                value = kwargs[param.name]
                expected = param.type
                type_map = {
                    "string": str,
                    "integer": int,
                    "float": float,
                    "boolean": bool,
                }
                expected_type = type_map.get(expected)
                if expected_type and not isinstance(value, expected_type):
                    errors.append(
                        f"Parameter '{param.name}' must be {expected}, "
                        f"got {type(value).__name__}"
                    )
        return errors

    def schema(self) -> dict[str, Any]:
        """Return JSON-schema-like representation for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                p.name: {
                    "type": p.type,
                    "description": p.description,
                    "required": p.required,
                }
                for p in self.parameters
            },
        }

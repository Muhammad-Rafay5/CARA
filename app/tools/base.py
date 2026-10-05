"""
Base Tool implementation and common helpers for CARA.

Extends abstract Tool with standardized execution wrapping, timing,
structured error capture, and input validation.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

from app.core.exceptions import ToolExecutionError
from app.core.interfaces.tool import Tool, ToolParameter, ToolResult
from app.observability.logging import get_logger
from app.observability.metrics import metrics

logger = get_logger(__name__)


class BaseTool(Tool):
    """
    Common base class for tools providing:
    - Input validation according to ToolParameter definitions
    - Timing and metrics recording
    - Safe exception handling converting errors into ToolResult.fail
    """

    async def run(self, **kwargs: Any) -> ToolResult:
        """
        Public execution entrypoint with pre-validation and observability.
        """
        # Validate input schema
        validation_errors = self.validate_inputs(kwargs)
        if validation_errors:
            error_msg = f"Validation failed for tool '{self.name}': {'; '.join(validation_errors)}"
            logger.warning("Tool validation error", tool=self.name, errors=validation_errors)
            return ToolResult.fail(error=error_msg)

        start_time = time.perf_counter()
        try:
            result = await self.execute(**kwargs)
            duration_ms = (time.perf_counter() - start_time) * 1000
            metrics.record_tool_call(tool_name=self.name, success=result.success)
            result.metadata["duration_ms"] = round(duration_ms, 2)
            return result
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            metrics.record_tool_call(tool_name=self.name, success=False)
            logger.error("Tool execution failed with exception", tool=self.name, error=str(exc))
            return ToolResult.fail(
                error=f"Execution of tool '{self.name}' failed: {str(exc)}",
                duration_ms=round(duration_ms, 2),
            )

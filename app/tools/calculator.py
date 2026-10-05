"""
Safe AST-Based Calculator Tool for CARA.

Evaluates mathematical and statistical expressions without using eval() or exec().
Supported Operations:
- Arithmetic: +, -, *, /, //, %, **
- Unary: +, -
- Basic Math Functions: sin, cos, tan, sqrt, log, log10, exp, abs, round, min, max, sum, pow
- Constants: pi, e
"""

from __future__ import annotations

import ast
import math
import operator
from typing import Any, Callable, Dict, List

from app.core.interfaces.tool import ToolParameter, ToolResult
from app.observability.logging import get_logger
from app.tools.base import BaseTool

logger = get_logger(__name__)

# Supported binary operators
_SAFE_OPERATORS: Dict[type, Callable[..., Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Supported math functions and constants
_SAFE_NAMES: Dict[str, Any] = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "pow": pow,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "pi": math.pi,
    "e": math.e,
}


class CalculatorTool(BaseTool):
    """
    Mathematical computation tool using pure AST parsing.
    Strictly forbids eval() and exec().
    """

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return (
            "Safely evaluate mathematical and scientific calculations using AST parsing. "
            "Supports basic arithmetic (+, -, *, /, **, //, %), constants (pi, e), "
            "and functions (sqrt, log, log10, exp, sin, cos, tan, abs, round, min, max)."
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="expression",
                type="string",
                description="The mathematical formula/expression to evaluate (e.g., 'sqrt(144) + 2**3').",
                required=True,
            )
        ]

    def _eval_node(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Expression):
            return self._eval_node(node.body)

        elif isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Unsupported constant type: {type(node.value).__name__}")

        elif isinstance(node, ast.Name):
            if node.id in _SAFE_NAMES:
                return _SAFE_NAMES[node.id]
            raise ValueError(f"Unknown or forbidden identifier: '{node.id}'")

        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            op_type = type(node.op)
            if op_type in _SAFE_OPERATORS:
                # Prevent extreme exponents causing DoS
                if op_type is ast.Pow and (isinstance(right, (int, float)) and right > 1000):
                    raise ValueError("Exponent too large (max 1000)")
                return _SAFE_OPERATORS[op_type](left, right)
            raise ValueError(f"Unsupported binary operator: {op_type.__name__}")

        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            op_type = type(node.op)
            if op_type in _SAFE_OPERATORS:
                return _SAFE_OPERATORS[op_type](operand)
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")

        elif isinstance(node, ast.Call):
            func = self._eval_node(node.func)
            if not callable(func):
                raise ValueError(f"Target is not a callable function: {node.func}")
            args = [self._eval_node(arg) for arg in node.args]
            return func(*args)

        elif isinstance(node, ast.List):
            return [self._eval_node(elem) for elem in node.elts]

        elif isinstance(node, ast.Tuple):
            return tuple(self._eval_node(elem) for elem in node.elts)

        else:
            raise ValueError(f"Unsupported AST node expression: {type(node).__name__}")

    async def execute(self, **kwargs: Any) -> ToolResult:
        expression = kwargs.get("expression", "").strip()
        if not expression:
            return ToolResult.fail("Empty expression provided.")

        try:
            tree = ast.parse(expression, mode="eval")
            result = self._eval_node(tree)
            return ToolResult.ok(
                data=result,
                expression=expression,
            )
        except ZeroDivisionError:
            return ToolResult.fail("Division by zero error.")
        except Exception as exc:
            return ToolResult.fail(f"Mathematical syntax error: {str(exc)}")

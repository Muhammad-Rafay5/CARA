"""
Integration tests for Tool Registry, AST Calculator, and SSRF URL Reader.
"""

import pytest
from app.tools.calculator import CalculatorTool
from app.tools.registry import tool_registry
from app.tools.url_reader import URLReaderTool


@pytest.mark.asyncio
async def test_calculator_ast_operations():
    calc = CalculatorTool()
    res = await calc.run(expression="sqrt(144) + 2**4")
    assert res.success is True
    assert res.data == 28.0

    # Test error handling (division by zero)
    res_zero = await calc.run(expression="10 / 0")
    assert res_zero.success is False


@pytest.mark.asyncio
async def test_url_reader_ssrf_blocking():
    reader = URLReaderTool()
    # Test blocked localhost and private ranges
    for blocked_url in ["http://localhost:8080", "http://127.0.0.1/admin", "http://192.168.1.1"]:
        res = await reader.run(url=blocked_url)
        assert res.success is False
        assert "SSRF" in res.error or "blocked" in res.error

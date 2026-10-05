"""
Integration test for Model Fallback Chain.
"""

import pytest
from app.core.interfaces.model import ModelMessage
from app.models.fallback import FallbackChain
from app.models.providers.ollama import OllamaProvider


@pytest.mark.asyncio
async def test_fallback_chain_structure():
    chain = FallbackChain(providers={})
    assert len(chain.provider_chain) >= 4

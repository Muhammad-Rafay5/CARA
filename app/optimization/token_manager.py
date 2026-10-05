"""
Token Manager for CARA.

Tracks token consumption across input (prompt) and output (completion) streams.
Provides estimation heuristics when exact counts are unavailable from raw responses.
"""

from __future__ import annotations

from typing import Dict, Optional
from app.core.constants import TOKENS_PER_CHAR_ESTIMATE


class TokenManager:
    """
    Manages cumulative token accounting.
    """

    def __init__(self):
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    def record(self, input_tokens: int, output_tokens: int) -> int:
        """
        Record consumed tokens and return incremental sum.
        """
        self._total_input_tokens += input_tokens
        self._total_output_tokens += output_tokens
        return input_tokens + output_tokens

    def estimate_tokens(self, text: str) -> int:
        """
        Rough estimate of token count: 1 token ≈ 4 characters.
        """
        if not text:
            return 0
        return max(1, int(len(text) * TOKENS_PER_CHAR_ESTIMATE))

    @property
    def total_tokens(self) -> int:
        return self._total_input_tokens + self._total_output_tokens


token_manager = TokenManager()

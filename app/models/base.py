"""
Base provider mixin for CARA LLM providers.
Provides shared retry logic, token estimation, and logging helpers
that all concrete provider implementations inherit.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from app.core.constants import (
    RETRY_BACKOFF_FACTOR,
    RETRY_BASE_DELAY_SECONDS,
    RETRY_MAX_DELAY_SECONDS,
)
from app.core.exceptions import ModelProviderError, RateLimitError
from app.core.interfaces.model import ModelMessage, ModelProvider, ModelResponse
from app.observability.logging import get_logger

logger = get_logger(__name__)


class BaseModelProvider(ModelProvider):
    """
    Abstract mixin that all CARA provider implementations extend.

    Adds:
    - Shared structured logging on every call.
    - Exponential-backoff retry (respects RateLimitError.retry_after_seconds).
    - Token estimation fallback for providers that don't return counts.
    """

    # Subclasses override this to set their max retry attempts
    _max_retries: int = 2

    async def generate_with_retry(
        self,
        messages: list[ModelMessage],
        *,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> ModelResponse:
        """
        Wrap self.generate() with exponential-backoff retries.

        Retries on transient ModelProviderError. Immediately re-raises
        RateLimitError (let the fallback chain handle it) after 1 attempt.
        """
        last_exc: Exception | None = None
        delay = RETRY_BASE_DELAY_SECONDS

        for attempt in range(1, self._max_retries + 2):  # +2: first try + retries
            try:
                start = time.monotonic()
                response = await self.generate(
                    messages, temperature=temperature, max_tokens=max_tokens, **kwargs
                )
                response.latency_ms = (time.monotonic() - start) * 1000
                logger.info(
                    "provider_call_success",
                    provider=self.provider_name,
                    model=self.model_name,
                    attempt=attempt,
                    latency_ms=round(response.latency_ms, 1),
                    tokens=response.total_tokens,
                )
                return response

            except RateLimitError as exc:
                logger.warning(
                    "provider_rate_limited",
                    provider=self.provider_name,
                    retry_after=exc.retry_after_seconds,
                )
                raise  # Let fallback chain handle immediately

            except ModelProviderError as exc:
                last_exc = exc
                logger.warning(
                    "provider_call_failed",
                    provider=self.provider_name,
                    attempt=attempt,
                    max_attempts=self._max_retries + 1,
                    error=str(exc),
                )
                if attempt <= self._max_retries:
                    await asyncio.sleep(min(delay, RETRY_MAX_DELAY_SECONDS))
                    delay *= RETRY_BACKOFF_FACTOR

        raise last_exc or ModelProviderError(
            "Unknown error after retries", provider=self.provider_name
        )

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Rough token estimate when provider doesn't return counts.
        1 token ≈ 4 characters (GPT-style tokenizer heuristic).
        """
        return max(1, len(text) // 4)

    def _messages_to_text(self, messages: list[ModelMessage]) -> str:
        """Concatenate all message content for token estimation."""
        return " ".join(m.content for m in messages)

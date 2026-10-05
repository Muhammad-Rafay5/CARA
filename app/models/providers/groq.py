"""
Groq Cloud LLM provider for CARA.

Supported models (free tier / very fast):
  - llama-3.1-8b-instant   → TIER_FAST
  - llama-3.3-70b-versatile → TIER_STANDARD
  - mixtral-8x7b-32768      → TIER_STANDARD (large context)

Requires: GROQ_API_KEY in environment.
SDK: groq>=0.9.0
"""

from __future__ import annotations

from typing import Any

from groq import AsyncGroq
from groq import APIError as GroqAPIError
from groq import RateLimitError as GroqRateLimitError
from groq import APIConnectionError as GroqConnectionError

from app.core.constants import PROVIDER_GROQ, TIER_FAST, TIER_STANDARD
from app.core.exceptions import ModelProviderError, ProviderUnavailableError, RateLimitError
from app.core.interfaces.model import ModelCapabilities, ModelMessage, ModelResponse
from app.models.base import BaseModelProvider
from app.observability.logging import get_logger

logger = get_logger(__name__)

# ── Model catalogue ───────────────────────────────────────────────────────────
GROQ_MODELS: dict[str, dict[str, Any]] = {
    "llama-3.1-8b-instant": {
        "tier": TIER_FAST,
        "context_tokens": 131_072,
        "output_tokens": 8_192,
        "cost_input_per_1k": 0.0,   # free tier
        "cost_output_per_1k": 0.0,
    },
    "llama-3.3-70b-versatile": {
        "tier": TIER_STANDARD,
        "context_tokens": 131_072,
        "output_tokens": 32_768,
        "cost_input_per_1k": 0.0,   # free tier
        "cost_output_per_1k": 0.0,
    },
    "mixtral-8x7b-32768": {
        "tier": TIER_STANDARD,
        "context_tokens": 32_768,
        "output_tokens": 32_768,
        "cost_input_per_1k": 0.0,
        "cost_output_per_1k": 0.0,
    },
}

DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"


class GroqProvider(BaseModelProvider):
    """
    Groq Cloud provider — fastest inference, free tier, ideal for SIMPLE tasks.

    Instantiate once and reuse; the underlying AsyncGroq client is thread-safe.
    """

    _max_retries = 2

    def __init__(self, api_key: str, model: str = DEFAULT_GROQ_MODEL) -> None:
        if model not in GROQ_MODELS:
            raise ValueError(
                f"Unknown Groq model '{model}'. "
                f"Available: {list(GROQ_MODELS.keys())}"
            )
        self._api_key = api_key
        self._model = model
        self._meta = GROQ_MODELS[model]
        self._client = AsyncGroq(api_key=api_key)

    # ── ModelProvider contract ────────────────────────────────────────────────

    @property
    def provider_name(self) -> str:
        return PROVIDER_GROQ

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            supports_streaming=True,
            supports_tool_use=True,
            supports_vision=False,
            max_context_tokens=self._meta["context_tokens"],
            max_output_tokens=self._meta["output_tokens"],
        )

    async def generate(
        self,
        messages: list[ModelMessage],
        *,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> ModelResponse:
        """Call Groq chat completions API."""
        payload = [{"role": m.role, "content": m.content} for m in messages]

        try:
            completion = await self._client.chat.completions.create(
                model=self._model,
                messages=payload,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=min(max_tokens, self._meta["output_tokens"]),
            )
        except GroqRateLimitError as exc:
            raise RateLimitError(provider=PROVIDER_GROQ) from exc
        except GroqConnectionError as exc:
            raise ProviderUnavailableError(provider=PROVIDER_GROQ) from exc
        except GroqAPIError as exc:
            raise ModelProviderError(
                f"Groq API error: {exc.message}",
                provider=PROVIDER_GROQ,
            ) from exc

        choice = completion.choices[0]
        usage = completion.usage

        return ModelResponse(
            content=choice.message.content or "",
            model=self._model,
            provider=PROVIDER_GROQ,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
            finish_reason=choice.finish_reason or "stop",
        )

    async def health_check(self) -> bool:
        """Ping Groq with a minimal completion to verify connectivity."""
        try:
            await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            return True
        except Exception as exc:
            logger.warning("groq_health_check_failed", error=str(exc))
            return False

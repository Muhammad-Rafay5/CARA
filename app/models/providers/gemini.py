"""
Google Gemini LLM provider for CARA.

Supported models:
  - gemini-2.0-flash-exp    → TIER_FAST     (free, fastest)
  - gemini-1.5-flash        → TIER_STANDARD (free, balanced)
  - gemini-1.5-pro          → TIER_ADVANCED (paid, strongest)

Requires: GEMINI_API_KEY in environment.
SDK: google-genai>=1.0.0
"""

from __future__ import annotations

from typing import Any

import google.genai as genai
from google.genai import types as genai_types

from app.core.constants import PROVIDER_GEMINI, TIER_ADVANCED, TIER_FAST, TIER_STANDARD
from app.core.exceptions import ModelProviderError, ProviderUnavailableError, RateLimitError
from app.core.interfaces.model import ModelCapabilities, ModelMessage, ModelResponse
from app.models.base import BaseModelProvider
from app.observability.logging import get_logger

logger = get_logger(__name__)

# ── Model catalogue ───────────────────────────────────────────────────────────
GEMINI_MODELS: dict[str, dict[str, Any]] = {
    "gemini-2.0-flash-exp": {
        "tier": TIER_FAST,
        "context_tokens": 1_048_576,
        "output_tokens": 8_192,
        "cost_input_per_1k": 0.0,
        "cost_output_per_1k": 0.0,
    },
    "gemini-1.5-flash": {
        "tier": TIER_STANDARD,
        "context_tokens": 1_048_576,
        "output_tokens": 8_192,
        "cost_input_per_1k": 0.000_075,
        "cost_output_per_1k": 0.000_30,
    },
    "gemini-1.5-pro": {
        "tier": TIER_ADVANCED,
        "context_tokens": 2_097_152,
        "output_tokens": 8_192,
        "cost_input_per_1k": 0.00_125,
        "cost_output_per_1k": 0.005,
    },
}

DEFAULT_GEMINI_MODEL = "gemini-2.0-flash-exp"

# Role mapping: CARA → Gemini SDK
_ROLE_MAP = {"user": "user", "assistant": "model", "system": "user"}


class GeminiProvider(BaseModelProvider):
    """
    Google Gemini provider — massive context window, vision support, free flash tier.
    Best for MEDIUM/COMPLEX tasks and as primary provider.
    """

    _max_retries = 2

    def __init__(self, api_key: str, model: str = DEFAULT_GEMINI_MODEL) -> None:
        if model not in GEMINI_MODELS:
            raise ValueError(
                f"Unknown Gemini model '{model}'. "
                f"Available: {list(GEMINI_MODELS.keys())}"
            )
        self._api_key = api_key
        self._model = model
        self._meta = GEMINI_MODELS[model]
        # Initialise the client with the API key
        self._client = genai.Client(api_key=api_key)

    # ── ModelProvider contract ────────────────────────────────────────────────

    @property
    def provider_name(self) -> str:
        return PROVIDER_GEMINI

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            supports_streaming=True,
            supports_tool_use=True,
            supports_vision=True,
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
        """Call Gemini generate_content API."""
        # Extract system instruction if first message is system role
        system_instruction: str | None = None
        chat_messages = messages

        if messages and messages[0].role == "system":
            system_instruction = messages[0].content
            chat_messages = messages[1:]

        # Build content list
        contents = [
            genai_types.Content(
                role=_ROLE_MAP.get(m.role, "user"),
                parts=[genai_types.Part(text=m.content)],
            )
            for m in chat_messages
        ]

        config = genai_types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=min(max_tokens, self._meta["output_tokens"]),
            system_instruction=system_instruction,
        )

        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            exc_str = str(exc).lower()
            if "429" in exc_str or "quota" in exc_str or "rate" in exc_str:
                raise RateLimitError(provider=PROVIDER_GEMINI) from exc
            if "unavailable" in exc_str or "connection" in exc_str:
                raise ProviderUnavailableError(provider=PROVIDER_GEMINI) from exc
            raise ModelProviderError(
                f"Gemini API error: {exc}",
                provider=PROVIDER_GEMINI,
            ) from exc

        # Extract text
        content_text = ""
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text"):
                    content_text += part.text

        # Extract token usage
        usage = response.usage_metadata
        prompt_tokens = getattr(usage, "prompt_token_count", 0) or 0
        completion_tokens = getattr(usage, "candidates_token_count", 0) or 0

        return ModelResponse(
            content=content_text,
            model=self._model,
            provider=PROVIDER_GEMINI,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            finish_reason=str(
                response.candidates[0].finish_reason
            ) if response.candidates else "stop",
        )

    async def health_check(self) -> bool:
        """Minimal health probe — 1-token generation."""
        try:
            await self._client.aio.models.generate_content(
                model=self._model,
                contents="ping",
                config=genai_types.GenerateContentConfig(max_output_tokens=1),
            )
            return True
        except Exception as exc:
            logger.warning("gemini_health_check_failed", error=str(exc))
            return False

"""
OpenRouter LLM provider for CARA.

OpenRouter is an API aggregator providing access to 100+ models
through a single OpenAI-compatible endpoint.

Primary use: fallback tier when Groq and Gemini are unavailable.
Free models available (e.g. mistralai/mistral-7b-instruct:free).

Requires: OPENROUTER_API_KEY in environment.
Uses: httpx (already a project dependency) — no extra SDK needed.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.constants import PROVIDER_OPENROUTER, TIER_FAST, TIER_STANDARD
from app.core.exceptions import ModelProviderError, ProviderUnavailableError, RateLimitError
from app.core.interfaces.model import ModelCapabilities, ModelMessage, ModelResponse
from app.models.base import BaseModelProvider
from app.observability.logging import get_logger

logger = get_logger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# ── Model catalogue ───────────────────────────────────────────────────────────
OPENROUTER_MODELS: dict[str, dict[str, Any]] = {
    "mistralai/mistral-7b-instruct:free": {
        "tier": TIER_FAST,
        "context_tokens": 32_768,
        "output_tokens": 4_096,
        "cost_input_per_1k": 0.0,
        "cost_output_per_1k": 0.0,
    },
    "meta-llama/llama-3.1-8b-instruct:free": {
        "tier": TIER_FAST,
        "context_tokens": 131_072,
        "output_tokens": 4_096,
        "cost_input_per_1k": 0.0,
        "cost_output_per_1k": 0.0,
    },
    "meta-llama/llama-3.3-70b-instruct": {
        "tier": TIER_STANDARD,
        "context_tokens": 131_072,
        "output_tokens": 8_192,
        "cost_input_per_1k": 0.000_06,
        "cost_output_per_1k": 0.000_06,
    },
}

DEFAULT_OPENROUTER_MODEL = "mistralai/mistral-7b-instruct:free"


class OpenRouterProvider(BaseModelProvider):
    """
    OpenRouter provider — 100+ model fallback, OpenAI-compatible REST API.
    Used as tier-3 fallback when primary providers are unavailable.

    Communicates via raw httpx rather than an SDK to avoid an extra dependency.
    """

    _max_retries = 2

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_OPENROUTER_MODEL,
        site_url: str = "https://github.com/cara-agent",
        site_name: str = "CARA Research Agent",
    ) -> None:
        if model not in OPENROUTER_MODELS:
            raise ValueError(
                f"Unknown OpenRouter model '{model}'. "
                f"Available: {list(OPENROUTER_MODELS.keys())}"
            )
        self._api_key = api_key
        self._model = model
        self._meta = OPENROUTER_MODELS[model]
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": site_url,
            "X-Title": site_name,
            "Content-Type": "application/json",
        }
        self._http = httpx.AsyncClient(
            base_url=OPENROUTER_BASE_URL,
            headers=self._headers,
            timeout=30.0,
        )

    # ── ModelProvider contract ────────────────────────────────────────────────

    @property
    def provider_name(self) -> str:
        return PROVIDER_OPENROUTER

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            supports_streaming=False,
            supports_tool_use=False,
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
        """Call OpenRouter chat completions endpoint."""
        payload = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": min(max_tokens, self._meta["output_tokens"]),
        }

        try:
            resp = await self._http.post("/chat/completions", json=payload)
        except httpx.ConnectError as exc:
            raise ProviderUnavailableError(provider=PROVIDER_OPENROUTER) from exc
        except httpx.TimeoutException as exc:
            raise ModelProviderError(
                "OpenRouter request timed out.",
                provider=PROVIDER_OPENROUTER,
            ) from exc

        if resp.status_code == 429:
            raise RateLimitError(provider=PROVIDER_OPENROUTER)
        if resp.status_code in (502, 503, 504):
            raise ProviderUnavailableError(provider=PROVIDER_OPENROUTER)
        if resp.status_code != 200:
            raise ModelProviderError(
                f"OpenRouter HTTP {resp.status_code}: {resp.text[:200]}",
                provider=PROVIDER_OPENROUTER,
            )

        data = resp.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})

        return ModelResponse(
            content=choice["message"]["content"] or "",
            model=self._model,
            provider=PROVIDER_OPENROUTER,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            finish_reason=choice.get("finish_reason", "stop"),
        )

    async def health_check(self) -> bool:
        """Check OpenRouter reachability via 1-token call."""
        try:
            resp = await self._http.post(
                "/chat/completions",
                json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                },
            )
            return resp.status_code == 200
        except Exception as exc:
            logger.warning("openrouter_health_check_failed", error=str(exc))
            return False

    async def close(self) -> None:
        """Close the underlying httpx client."""
        await self._http.aclose()

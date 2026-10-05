"""
Ollama local LLM provider for CARA.

Ollama runs models locally — zero API cost, works offline.
Used as the last-resort fallback when all cloud providers are unavailable.

Requires: Ollama process running at OLLAMA_BASE_URL (default: http://localhost:11434)
Pull a model first: `ollama pull llama3.2`

No extra SDK needed — uses httpx REST calls to Ollama's OpenAI-compatible API.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.constants import PROVIDER_OLLAMA, TIER_FAST
from app.core.exceptions import ModelProviderError, ProviderUnavailableError
from app.core.interfaces.model import ModelCapabilities, ModelMessage, ModelResponse
from app.models.base import BaseModelProvider
from app.observability.logging import get_logger

logger = get_logger(__name__)

DEFAULT_OLLAMA_MODEL = "llama3.2"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"


class OllamaProvider(BaseModelProvider):
    """
    Ollama local inference provider — last-resort fallback, zero cost.

    Uses Ollama's OpenAI-compatible /v1/chat/completions endpoint.
    Only available when Ollama daemon is running locally.
    """

    _max_retries = 1  # Local calls either work or fail fast

    def __init__(
        self,
        base_url: str = DEFAULT_OLLAMA_BASE_URL,
        model: str = DEFAULT_OLLAMA_MODEL,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._http = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=60.0,   # Local inference can be slow
        )

    # ── ModelProvider contract ────────────────────────────────────────────────

    @property
    def provider_name(self) -> str:
        return PROVIDER_OLLAMA

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            supports_streaming=False,
            supports_tool_use=False,
            supports_vision=False,
            max_context_tokens=8_192,
            max_output_tokens=4_096,
        )

    async def generate(
        self,
        messages: list[ModelMessage],
        *,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> ModelResponse:
        """
        Call Ollama's OpenAI-compatible /v1/chat/completions endpoint.
        Falls back to /api/generate if the v1 path isn't available.
        """
        payload = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": min(max_tokens, 4096),
            },
        }

        try:
            resp = await self._http.post("/v1/chat/completions", json=payload)
        except httpx.ConnectError as exc:
            raise ProviderUnavailableError(provider=PROVIDER_OLLAMA) from exc
        except httpx.TimeoutException as exc:
            raise ModelProviderError(
                "Ollama request timed out — model may still be loading.",
                provider=PROVIDER_OLLAMA,
            ) from exc

        if resp.status_code == 404:
            # Fallback to native /api/chat endpoint
            return await self._generate_native(messages, temperature, max_tokens)

        if resp.status_code != 200:
            raise ModelProviderError(
                f"Ollama HTTP {resp.status_code}: {resp.text[:200]}",
                provider=PROVIDER_OLLAMA,
            )

        data = resp.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})

        return ModelResponse(
            content=choice["message"]["content"] or "",
            model=self._model,
            provider=PROVIDER_OLLAMA,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            finish_reason=choice.get("finish_reason", "stop"),
        )

    async def _generate_native(
        self,
        messages: list[ModelMessage],
        temperature: float,
        max_tokens: int,
    ) -> ModelResponse:
        """Use Ollama's native /api/chat endpoint."""
        payload = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        resp = await self._http.post("/api/chat", json=payload)
        if resp.status_code != 200:
            raise ModelProviderError(
                f"Ollama native API error {resp.status_code}: {resp.text[:200]}",
                provider=PROVIDER_OLLAMA,
            )
        data = resp.json()
        content = data.get("message", {}).get("content", "")
        # Ollama native doesn't return token counts reliably
        est_tokens = self.estimate_tokens(content)

        return ModelResponse(
            content=content,
            model=self._model,
            provider=PROVIDER_OLLAMA,
            total_tokens=est_tokens,
            finish_reason="stop",
        )

    async def health_check(self) -> bool:
        """Check if Ollama daemon is reachable."""
        try:
            resp = await self._http.get("/api/tags")
            return resp.status_code == 200
        except Exception as exc:
            logger.warning("ollama_health_check_failed", error=str(exc))
            return False

    async def list_local_models(self) -> list[str]:
        """Return names of locally available Ollama models."""
        try:
            resp = await self._http.get("/api/tags")
            if resp.status_code == 200:
                return [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            pass
        return []

    async def close(self) -> None:
        """Close the underlying httpx client."""
        await self._http.aclose()

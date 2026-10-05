"""
Fallback Chain Execution for Model Providers in CARA.

Implements resilient sequential fallback when providers fail or return rate limits:
Preferred Priority Order:
    Gemini -> Groq -> OpenRouter -> Ollama (local)

Respects:
- Circuit breaker trip status (fails fast if OPEN).
- Rate limits (backs off or immediately tries next provider).
- Hard guardrail: AllProvidersFailedError if every fallback in chain is exhausted.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from app.core.constants import (
    PROVIDER_GEMINI,
    PROVIDER_GROQ,
    PROVIDER_OLLAMA,
    PROVIDER_OPENROUTER,
)
from app.core.exceptions import (
    AllProvidersFailedError,
    ModelProviderError,
    ProviderUnavailableError,
    RateLimitError,
)
from app.core.interfaces.model import ModelMessage, ModelProvider, ModelResponse
from app.models.registry import ModelProfile, ModelRegistry, registry as default_registry
from app.models.usage import usage_tracker
from app.observability.logging import get_logger
from app.recovery.circuit_breaker import circuit_breakers

logger = get_logger(__name__)

DEFAULT_PROVIDER_CHAIN: List[str] = [
    PROVIDER_GEMINI,
    PROVIDER_GROQ,
    PROVIDER_OPENROUTER,
    PROVIDER_OLLAMA,
]


class FallbackChain:
    """
    Executes model generation across a fallback priority sequence of providers.
    """

    def __init__(
        self,
        providers: Dict[str, ModelProvider],
        registry: Optional[ModelRegistry] = None,
        provider_chain: Optional[List[str]] = None,
    ):
        self.providers = providers
        self.registry = registry or default_registry
        self.provider_chain = provider_chain or DEFAULT_PROVIDER_CHAIN

    async def generate(
        self,
        messages: List[ModelMessage],
        initial_profile: Optional[ModelProfile] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stop_sequences: Optional[List[str]] = None,
    ) -> ModelResponse:
        """
        Attempt generation using the initial profile or top available provider,
        falling back through the chain on transient or unrecoverable provider failures.
        """
        # Determine candidate provider sequence
        chain = list(self.provider_chain)
        if initial_profile and initial_profile.provider in chain:
            # Move initial preferred provider to the front
            chain.remove(initial_profile.provider)
            chain.insert(0, initial_profile.provider)

        last_error: Optional[Exception] = None

        for provider_name in chain:
            provider = self.providers.get(provider_name)
            if not provider:
                logger.debug("Provider not configured in chain, skipping", provider=provider_name)
                continue

            # Check circuit breaker before attempting call
            breaker = circuit_breakers.get(provider_name)
            if not breaker.can_execute():
                logger.warning("Circuit breaker OPEN for provider, skipping", provider=provider_name)
                continue

            try:
                # Find an appropriate model name for this provider
                model_name = (
                    initial_profile.model_name
                    if (initial_profile and initial_profile.provider == provider_name)
                    else provider.default_model
                )

                logger.info(
                    "Attempting model execution via fallback chain",
                    provider=provider_name,
                    model=model_name,
                )

                response = await provider.generate(
                    messages=messages,
                    model=model_name,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stop_sequences=stop_sequences,
                )

                # Record success on circuit breaker & usage tracker
                breaker.record_success()
                usage_tracker.record_usage(response)

                logger.info(
                    "Model execution succeeded via fallback chain",
                    provider=provider_name,
                    model=model_name,
                    total_tokens=response.total_tokens,
                    duration_ms=response.duration_ms,
                )
                return response

            except (RateLimitError, ProviderUnavailableError, ModelProviderError) as exc:
                breaker.record_failure(exc)
                last_error = exc
                logger.warning(
                    "Provider attempt failed in fallback chain, advancing to next",
                    provider=provider_name,
                    error=str(exc),
                )
            except Exception as exc:
                breaker.record_failure(exc)
                last_error = exc
                logger.error(
                    "Unexpected error from provider in fallback chain",
                    provider=provider_name,
                    error=str(exc),
                )

        error_msg = f"All providers in fallback chain failed. Last error: {last_error}"
        logger.error(error_msg)
        raise AllProvidersFailedError(error_msg)

"""
Abstract Model Provider Interface for CARA.
All LLM provider implementations must conform to this contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator


@dataclass
class ModelMessage:
    """Represents a single message in a conversation."""

    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class ModelResponse:
    """Structured response from any model provider."""

    content: str
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    finish_reason: str = "stop"
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def total_cost_usd(self) -> float:
        """Cost is tracked externally by cost_tracker; placeholder here."""
        return 0.0


@dataclass
class ModelCapabilities:
    """Describes what a specific model/provider can do."""

    supports_streaming: bool = False
    supports_tool_use: bool = False
    supports_vision: bool = False
    max_context_tokens: int = 8192
    max_output_tokens: int = 4096


class ModelProvider(ABC):
    """
    Abstract base class for all LLM provider implementations.

    Implementations MUST NOT use global state. Each call is stateless
    at the provider level; conversation history is managed by the caller.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier for this provider (e.g., 'groq', 'gemini')."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """The specific model variant in use (e.g., 'llama-3.1-8b-instant')."""

    @property
    @abstractmethod
    def capabilities(self) -> ModelCapabilities:
        """Static capability profile for this provider+model combo."""

    @abstractmethod
    async def generate(
        self,
        messages: list[ModelMessage],
        *,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> ModelResponse:
        """
        Generate a response from the LLM.

        Args:
            messages: Ordered conversation history.
            temperature: Sampling temperature (0.0 = deterministic).
            max_tokens: Hard cap on completion tokens.
            **kwargs: Provider-specific overrides.

        Returns:
            ModelResponse with content and token usage.

        Raises:
            ModelProviderError: On provider-level failure.
            RateLimitError: On 429 / quota exhaustion.
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Verify that the provider endpoint is reachable and operational.

        Returns:
            True if healthy, False otherwise. Must never raise.
        """

    async def stream(
        self,
        messages: list[ModelMessage],
        *,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        Optional streaming interface. Default raises NotImplementedError.
        Override in providers that support streaming.
        """
        raise NotImplementedError(
            f"Provider '{self.provider_name}' does not support streaming."
        )
        # Unreachable, satisfies async generator type hint
        yield  # type: ignore[misc]

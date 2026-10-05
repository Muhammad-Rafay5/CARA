"""
Domain exceptions for CARA.
Provides a clean exception hierarchy used across all subsystems.
"""

from __future__ import annotations


# ── Base ────────────────────────────────────────────────────────────────────

class CARAError(Exception):
    """Root exception for all CARA domain errors."""

    def __init__(self, message: str, *, recoverable: bool = True) -> None:
        super().__init__(message)
        self.recoverable = recoverable


# ── Model / Provider ────────────────────────────────────────────────────────

class ModelProviderError(CARAError):
    """Raised when an LLM provider call fails."""

    def __init__(
        self,
        message: str,
        *,
        provider: str = "unknown",
        recoverable: bool = True,
    ) -> None:
        super().__init__(message, recoverable=recoverable)
        self.provider = provider


class RateLimitError(ModelProviderError):
    """Raised on HTTP 429 / quota exhaustion from an LLM provider."""

    def __init__(self, provider: str, retry_after_seconds: float = 60.0) -> None:
        super().__init__(
            f"Rate limited by provider '{provider}'. "
            f"Retry after {retry_after_seconds:.0f}s.",
            provider=provider,
            recoverable=True,
        )
        self.retry_after_seconds = retry_after_seconds


class ProviderUnavailableError(ModelProviderError):
    """Raised when a provider is offline or all retries are exhausted."""

    def __init__(self, provider: str) -> None:
        super().__init__(
            f"Provider '{provider}' is unavailable.",
            provider=provider,
            recoverable=True,  # recoverable via fallback chain
        )


class AllProvidersFailedError(CARAError):
    """Raised when every provider in the fallback chain has failed."""

    def __init__(self) -> None:
        super().__init__(
            "All LLM providers exhausted. Cannot complete the request.",
            recoverable=False,
        )


class BudgetExceededError(CARAError):
    """Raised when a hard resource limit (tokens, calls, cost) is breached."""

    def __init__(self, limit_type: str, limit_value: int | float | None = None) -> None:
        msg = (
            f"Hard limit exceeded: {limit_type}={limit_value}. Stopping to respect cost guardrails."
            if limit_value is not None
            else f"Hard limit exceeded: {limit_type}. Stopping to respect cost guardrails."
        )
        super().__init__(msg, recoverable=False)
        self.limit_type = limit_type
        self.limit_value = limit_value


# ── Tool ────────────────────────────────────────────────────────────────────

class ToolExecutionError(CARAError):
    """Raised when a tool call fails."""

    def __init__(self, tool_name: str, reason: str) -> None:
        super().__init__(
            f"Tool '{tool_name}' failed: {reason}",
            recoverable=True,
        )
        self.tool_name = tool_name


class SSRFBlockedError(ToolExecutionError):
    """Raised when URL reader detects a blocked/private IP address."""

    def __init__(self, url: str) -> None:
        super().__init__(
            tool_name="url_reader",
            reason=f"SSRF protection blocked URL: {url}",
        )
        self.url = url


# ── Storage / Cache ─────────────────────────────────────────────────────────

class StorageError(CARAError):
    """Raised on persistent storage read/write failures."""


class CacheError(CARAError):
    """Raised on cache backend failures."""


# ── Agent / Research ────────────────────────────────────────────────────────

class ResearchError(CARAError):
    """Raised when the research pipeline encounters an unrecoverable state."""


class VerificationError(CARAError):
    """Raised when verification fails beyond the recovery threshold."""


class ConfigurationError(CARAError):
    """Raised on missing or invalid application configuration."""

    def __init__(self, message: str) -> None:
        super().__init__(message, recoverable=False)

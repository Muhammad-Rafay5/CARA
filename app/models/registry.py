"""
Model Registry for CARA.

Maintains a catalogue of all available models with their capability profiles,
context limits, pricing metadata, and current availability status.

Design principles:
- Pure data — no LLM calls, no I/O.
- Thread-safe reads (Python GIL + immutable model profiles).
- Availability is updated by the health monitor (Phase 2.3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

from app.core.constants import (
    PROVIDER_GEMINI,
    PROVIDER_GROQ,
    PROVIDER_OLLAMA,
    PROVIDER_OPENROUTER,
    TIER_ADVANCED,
    TIER_FAST,
    TIER_STANDARD,
)
from app.observability.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ModelProfile:
    """
    Complete capability + cost profile for a single provider/model combination.

    Scores are normalised to [0.0, 1.0] and used by the selector's
    weighted scoring formula.
    """

    provider: str
    model_name: str
    tier: str

    # Context & output limits
    context_tokens: int
    output_tokens: int

    # Pricing (USD per 1k tokens; 0.0 = free)
    cost_input_per_1k: float = 0.0
    cost_output_per_1k: float = 0.0

    # Normalised capability scores [0.0 – 1.0]
    capability_score: float = 0.5      # overall intelligence / reasoning quality
    context_score: float = 0.5        # relative context window size
    tool_use_score: float = 0.0       # ability to call tools natively
    reliability_score: float = 0.8    # historical uptime estimate
    speed_score: float = 0.5          # tokens-per-second relative rank
    cost_efficiency_score: float = 0.5 # value per output token

    # Feature flags
    supports_streaming: bool = False
    supports_tools: bool = False
    supports_vision: bool = False
    is_local: bool = False

    # Runtime availability (updated by HealthMonitor)
    is_available: bool = True

    @property
    def full_id(self) -> str:
        """Unique registry key: 'provider:model_name'."""
        return f"{self.provider}:{self.model_name}"


# ── Built-in model catalogue ──────────────────────────────────────────────────

_DEFAULT_CATALOGUE: list[ModelProfile] = [
    # ── Groq (fast, free) ──────────────────────────────────────────────────
    ModelProfile(
        provider=PROVIDER_GROQ,
        model_name="llama-3.1-8b-instant",
        tier=TIER_FAST,
        context_tokens=131_072,
        output_tokens=8_192,
        capability_score=0.55,
        context_score=0.75,
        tool_use_score=0.6,
        reliability_score=0.85,
        speed_score=1.0,          # fastest available
        cost_efficiency_score=1.0,  # free
        supports_streaming=True,
        supports_tools=True,
    ),
    ModelProfile(
        provider=PROVIDER_GROQ,
        model_name="llama-3.3-70b-versatile",
        tier=TIER_STANDARD,
        context_tokens=131_072,
        output_tokens=32_768,
        capability_score=0.80,
        context_score=0.75,
        tool_use_score=0.75,
        reliability_score=0.85,
        speed_score=0.75,
        cost_efficiency_score=1.0,  # free
        supports_streaming=True,
        supports_tools=True,
    ),
    # ── Gemini (large context, free flash) ────────────────────────────────
    ModelProfile(
        provider=PROVIDER_GEMINI,
        model_name="gemini-2.0-flash-exp",
        tier=TIER_FAST,
        context_tokens=1_048_576,
        output_tokens=8_192,
        capability_score=0.70,
        context_score=1.0,        # largest context window
        tool_use_score=0.8,
        reliability_score=0.90,
        speed_score=0.90,
        cost_efficiency_score=1.0,  # free
        supports_streaming=True,
        supports_tools=True,
        supports_vision=True,
    ),
    ModelProfile(
        provider=PROVIDER_GEMINI,
        model_name="gemini-1.5-flash",
        tier=TIER_STANDARD,
        context_tokens=1_048_576,
        output_tokens=8_192,
        cost_input_per_1k=0.000_075,
        cost_output_per_1k=0.000_30,
        capability_score=0.80,
        context_score=1.0,
        tool_use_score=0.85,
        reliability_score=0.92,
        speed_score=0.85,
        cost_efficiency_score=0.90,
        supports_streaming=True,
        supports_tools=True,
        supports_vision=True,
    ),
    ModelProfile(
        provider=PROVIDER_GEMINI,
        model_name="gemini-1.5-pro",
        tier=TIER_ADVANCED,
        context_tokens=2_097_152,
        output_tokens=8_192,
        cost_input_per_1k=0.00_125,
        cost_output_per_1k=0.005,
        capability_score=0.98,
        context_score=1.0,
        tool_use_score=0.95,
        reliability_score=0.95,
        speed_score=0.55,
        cost_efficiency_score=0.45,
        supports_streaming=True,
        supports_tools=True,
        supports_vision=True,
    ),
    # ── OpenRouter (fallback, free tier) ─────────────────────────────────
    ModelProfile(
        provider=PROVIDER_OPENROUTER,
        model_name="mistralai/mistral-7b-instruct:free",
        tier=TIER_FAST,
        context_tokens=32_768,
        output_tokens=4_096,
        capability_score=0.50,
        context_score=0.40,
        tool_use_score=0.0,
        reliability_score=0.70,
        speed_score=0.65,
        cost_efficiency_score=1.0,
        supports_streaming=False,
        supports_tools=False,
    ),
    ModelProfile(
        provider=PROVIDER_OPENROUTER,
        model_name="meta-llama/llama-3.1-8b-instruct:free",
        tier=TIER_FAST,
        context_tokens=131_072,
        output_tokens=4_096,
        capability_score=0.55,
        context_score=0.75,
        tool_use_score=0.0,
        reliability_score=0.70,
        speed_score=0.65,
        cost_efficiency_score=1.0,
        supports_streaming=False,
        supports_tools=False,
    ),
    # ── Ollama (local, free, last resort) ────────────────────────────────
    ModelProfile(
        provider=PROVIDER_OLLAMA,
        model_name="llama3.2",
        tier=TIER_FAST,
        context_tokens=8_192,
        output_tokens=4_096,
        capability_score=0.45,
        context_score=0.20,
        tool_use_score=0.0,
        reliability_score=0.60,   # depends on local hardware
        speed_score=0.35,          # CPU inference
        cost_efficiency_score=1.0, # free
        supports_streaming=False,
        supports_tools=False,
        is_local=True,
    ),
]


class ModelRegistry:
    """
    Central registry of all available LLM model profiles.

    Provides lookup by full_id, tier, provider, or capability.
    Availability status is updated at runtime by the HealthMonitor.
    """

    def __init__(
        self, catalogue: list[ModelProfile] | None = None
    ) -> None:
        self._profiles: dict[str, ModelProfile] = {}
        for profile in (catalogue or _DEFAULT_CATALOGUE):
            self._profiles[profile.full_id] = profile

    def get(self, full_id: str) -> ModelProfile | None:
        """Retrieve a profile by 'provider:model_name'."""
        return self._profiles.get(full_id)

    def all(self) -> list[ModelProfile]:
        """Return all registered profiles."""
        return list(self._profiles.values())

    def available(self) -> list[ModelProfile]:
        """Return only profiles currently marked as available."""
        return [p for p in self._profiles.values() if p.is_available]

    def by_tier(self, tier: str) -> list[ModelProfile]:
        """Return available profiles for a given tier."""
        return [p for p in self.available() if p.tier == tier]

    def by_provider(self, provider: str) -> list[ModelProfile]:
        """Return available profiles for a given provider."""
        return [p for p in self.available() if p.provider == provider]

    def set_availability(self, full_id: str, available: bool) -> None:
        """Update availability status (called by HealthMonitor)."""
        if full_id in self._profiles:
            self._profiles[full_id].is_available = available
            logger.info(
                "model_availability_updated",
                model=full_id,
                available=available,
            )

    def set_provider_availability(self, provider: str, available: bool) -> None:
        """Update availability status for all models belonging to a provider."""
        for profile in self._profiles.values():
            if profile.provider == provider:
                profile.is_available = available
        logger.info(
            "provider_availability_updated",
            provider=provider,
            available=available,
        )

    def __iter__(self) -> Iterator[ModelProfile]:
        return iter(self._profiles.values())

    def __len__(self) -> int:
        return len(self._profiles)


# Application-lifetime singleton
registry = ModelRegistry()

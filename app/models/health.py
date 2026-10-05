"""
Provider Health Monitor for CARA.

Periodically pings or checks model providers, tracking consecutive failures,
response latency, and synchronizing availability with the ModelRegistry.
"""

from __future__ import annotations

import asyncio
from typing import Dict, Optional

from app.core.constants import (
    PROVIDER_GEMINI,
    PROVIDER_GROQ,
    PROVIDER_OLLAMA,
    PROVIDER_OPENROUTER,
)
from app.core.interfaces.model import ModelProvider
from app.models.registry import ModelRegistry, registry as default_registry
from app.observability.logging import get_logger
from app.recovery.circuit_breaker import circuit_breakers

logger = get_logger(__name__)


class HealthMonitor:
    """
    Monitors provider readiness and updates ModelRegistry availability flags.
    """

    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        providers: Optional[Dict[str, ModelProvider]] = None,
    ):
        self.registry = registry or default_registry
        self.providers = providers or {}

    def register_provider(self, name: str, provider: ModelProvider) -> None:
        self.providers[name] = provider

    async def check_provider(self, name: str) -> bool:
        """
        Check health of a specific provider.
        Returns True if healthy, False otherwise.
        """
        provider = self.providers.get(name)
        if not provider:
            logger.debug("No provider instance registered for health check", provider=name)
            return False

        breaker = circuit_breakers.get(name)
        if not breaker.can_execute():
            self.registry.set_provider_availability(name, False)
            return False

        try:
            is_healthy = await provider.health_check()
            if is_healthy:
                breaker.record_success()
                self.registry.set_provider_availability(name, True)
                logger.debug("Provider health check passed", provider=name)
                return True
            else:
                breaker.record_failure()
                self.registry.set_provider_availability(name, False)
                logger.warning("Provider health check failed", provider=name)
                return False
        except Exception as exc:
            breaker.record_failure(exc)
            self.registry.set_provider_availability(name, False)
            logger.warning("Exception during provider health check", provider=name, error=str(exc))
            return False

    async def check_all(self) -> Dict[str, bool]:
        """
        Check health of all registered providers concurrently.
        """
        if not self.providers:
            return {}

        tasks = {
            name: asyncio.create_task(self.check_provider(name))
            for name in self.providers
        }

        results = {}
        for name, task in tasks.items():
            results[name] = await task

        return results

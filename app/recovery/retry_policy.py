"""
Retry Policy for CARA.

Implements exponential backoff with jitter and max retry bounds.
"""

from __future__ import annotations

import asyncio
import random
from typing import Callable, TypeVar, Optional

from app.core.constants import (
    RETRY_BACKOFF_FACTOR,
    RETRY_BASE_DELAY_SECONDS,
    RETRY_MAX_DELAY_SECONDS,
)
from app.observability.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class RetryPolicy:
    """
    Exponential backoff retry policy manager.
    """

    def __init__(
        self,
        max_retries: int = 2,
        base_delay: float = RETRY_BASE_DELAY_SECONDS,
        max_delay: float = RETRY_MAX_DELAY_SECONDS,
        backoff_factor: float = RETRY_BACKOFF_FACTOR,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor

    def get_delay(self, attempt: int) -> float:
        """Calculate delay in seconds for a given attempt count (0-indexed)."""
        delay = self.base_delay * (self.backoff_factor ** attempt)
        jitter = random.uniform(0.0, 0.5 * self.base_delay)
        return min(delay + jitter, self.max_delay)

    async def execute_async(
        self,
        fn: Callable[[], Any],
        retry_exceptions: tuple = (Exception,),
        on_retry: Optional[Callable[[int, Exception, float], None]] = None,
    ) -> Any:
        """
        Execute an asynchronous function with bounded retries.
        """
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                return await fn()
            except retry_exceptions as exc:
                last_exception = exc
                if attempt >= self.max_retries:
                    logger.error("Max retries exceeded", attempt=attempt, error=str(exc))
                    raise exc

                delay = self.get_delay(attempt)
                logger.warning(
                    "Retrying operation after error",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    delay_seconds=round(delay, 2),
                    error=str(exc),
                )
                if on_retry:
                    on_retry(attempt, exc, delay)

                await asyncio.sleep(delay)

        raise last_exception

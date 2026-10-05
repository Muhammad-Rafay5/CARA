"""
Abstract Cache Interface for CARA.
Defines key-value caching contract used to eliminate duplicate research queries.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class CacheRepository(ABC):
    """
    Abstract async key-value cache.

    Used by the cost optimization layer to skip duplicate LLM/tool calls.
    Implementations include in-memory dict cache and Redis cache.
    """

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """
        Retrieve a cached value.

        Args:
            key: Cache lookup key.

        Returns:
            Cached value, or None on miss.
        """

    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """
        Store a value in the cache.

        Args:
            key: Cache key.
            value: Value to cache (must be JSON-serializable).
            ttl_seconds: Time-to-live in seconds (default: 1 hour).

        Raises:
            CacheError: On write failure.
        """

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Invalidate a cache entry.

        Args:
            key: The key to evict.

        Returns:
            True if the key was present and removed, False otherwise.
        """

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check whether a key exists in the cache (without retrieving value).

        Args:
            key: The key to check.

        Returns:
            True if cached, False on miss or expiry.
        """

    @abstractmethod
    async def clear(self) -> int:
        """
        Flush all entries from the cache.

        Returns:
            Number of entries removed.
        """

    async def get_or_set(
        self,
        key: str,
        factory: Any,
        ttl_seconds: int = 3600,
    ) -> Any:
        """
        Return cached value if present, otherwise call factory and cache result.

        Args:
            key: Cache key.
            factory: Async callable producing the value on cache miss.
            ttl_seconds: TTL for the newly cached value.

        Returns:
            Cached or freshly-computed value.
        """
        cached = await self.get(key)
        if cached is not None:
            return cached
        result = await factory()
        await self.set(key, result, ttl_seconds=ttl_seconds)
        return result

    async def close(self) -> None:
        """Release connection resources. Override in persistent implementations."""

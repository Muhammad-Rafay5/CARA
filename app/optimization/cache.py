"""
In-Memory Semantic & Exact Match Research Cache for CARA.

Prevents redundant web searches and expensive LLM generations for identical or
highly similar queries within a TTL window.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.observability.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    value: Any
    created_at: float
    ttl_seconds: float

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl_seconds


class ResearchCache:
    """
    Thread-safe in-memory cache for queries and tool outputs.
    """

    def __init__(self, default_ttl_seconds: float = 3600.0):
        self.default_ttl = default_ttl_seconds
        self._store: Dict[str, CacheEntry] = {}

    def _hash_key(self, key: str) -> str:
        return hashlib.sha256(key.strip().lower().encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        hashed = self._hash_key(key)
        entry = self._store.get(hashed)
        if not entry:
            return None

        if entry.is_expired:
            del self._store[hashed]
            return None

        logger.debug("Research cache hit", key=key[:40])
        return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        hashed = self._hash_key(key)
        self._store[hashed] = CacheEntry(
            value=value,
            created_at=time.time(),
            ttl_seconds=ttl or self.default_ttl,
        )

    def clear(self) -> None:
        self._store.clear()


research_cache = ResearchCache()

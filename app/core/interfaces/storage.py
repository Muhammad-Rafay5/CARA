"""
Abstract Storage Repository Interface for CARA.
Defines the contract for persisting research sessions and results.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class StorageRepository(ABC):
    """
    Abstract async storage backend.

    Implementations may use SQLite, PostgreSQL, or in-memory stores.
    All methods are async to support non-blocking I/O.
    """

    @abstractmethod
    async def save(self, key: str, value: Any) -> None:
        """
        Persist a value under the given key.

        Args:
            key: Unique storage key (e.g., research session ID).
            value: Serializable data object to store.

        Raises:
            StorageError: On write failure.
        """

    @abstractmethod
    async def load(self, key: str) -> Any | None:
        """
        Retrieve a value by key.

        Args:
            key: The storage key to look up.

        Returns:
            The stored value, or None if not found.

        Raises:
            StorageError: On read failure.
        """

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Remove a stored value.

        Args:
            key: The key to delete.

        Returns:
            True if the key existed and was deleted, False if not found.

        Raises:
            StorageError: On delete failure.
        """

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check whether a key exists in storage.

        Args:
            key: The key to check.

        Returns:
            True if present, False otherwise.
        """

    @abstractmethod
    async def list_keys(self, prefix: str = "") -> list[str]:
        """
        List all keys, optionally filtered by prefix.

        Args:
            prefix: Optional prefix to filter results.

        Returns:
            Sorted list of matching keys.
        """

    async def close(self) -> None:
        """
        Release any open connections or file handles.
        Override in implementations that hold persistent resources.
        """

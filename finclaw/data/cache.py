"""Simple in-memory TTL cache for data source results."""

from __future__ import annotations

import time
from typing import Any


class TTLCache:
    """Thread-safe in-memory cache with per-key TTL."""

    def __init__(self, default_ttl: int = 3600):
        self._store: dict[str, tuple[Any, float]] = {}
        self._default_ttl = default_ttl

    def get(self, key: str) -> Any | None:
        """Return cached value if present and not expired, else None."""
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a value with TTL in seconds."""
        expires_at = time.monotonic() + (ttl if ttl is not None else self._default_ttl)
        self._store[key] = (value, expires_at)

    def invalidate(self, key: str) -> None:
        """Remove a specific key."""
        self._store.pop(key, None)

    def clear(self) -> None:
        """Remove all entries."""
        self._store.clear()

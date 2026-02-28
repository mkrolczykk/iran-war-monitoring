"""
Simple in-memory cache with TTL support.
Used for HTTP response caching in scrapers.
"""

from __future__ import annotations

import time
from typing import Any, Optional


class TTLCache:
    """Dictionary-like cache where entries expire after *ttl* seconds."""

    def __init__(self, ttl: int = 55) -> None:
        self._ttl = ttl
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, value = entry
        if time.time() - ts > self._ttl:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (time.time(), value)

    def clear(self) -> None:
        self._store.clear()

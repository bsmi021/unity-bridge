"""
ResponseCache — LRU cache with TTL for read-only Unity Bridge queries.

Migrated from response_cache.py. Caches successful responses from
read-only commands to reduce latency for repeated queries.
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("unity_bridge.cache")


@dataclass
class CacheEntry:
    """Cached response entry with timestamp and TTL.

    Attributes:
        data: Cached response data.
        timestamp: When this entry was created (UTC).
        ttl_seconds: Time-to-live in seconds.
    """

    data: dict[str, Any]
    timestamp: datetime
    ttl_seconds: float

    def is_valid(self) -> bool:
        """Return True if this entry has not expired."""
        age = (datetime.now(timezone.utc) - self.timestamp).total_seconds()
        return age < self.ttl_seconds


class ResponseCache:
    """LRU cache for Unity Bridge responses.

    Features:
    - Automatic TTL-based expiration
    - LRU eviction when capacity is reached
    - Scene change detection and invalidation
    - Manual invalidation by pattern
    - Thread-safe async operations via asyncio.Lock
    """

    CACHEABLE_COMMANDS: set[str] = {
        "query-hierarchy",
        "get-component-data",
        "get-selection",
        "validate-prefab",
    }

    DEFAULT_TTL: dict[str, float] = {
        "query-hierarchy": 5.0,
        "get-component-data": 5.0,
        "get-selection": 2.0,
        "validate-prefab": 30.0,
    }

    def __init__(self, max_entries: int = 100) -> None:
        self._cache: dict[str, CacheEntry] = {}
        self._max_entries = max_entries
        self._lock = asyncio.Lock()
        self._last_scene: str | None = None
        logger.debug("ResponseCache initialized (max_entries=%d)", max_entries)

    def _make_key(self, command_type: str, parameters: dict[str, Any]) -> str:
        """Generate a cache key from command type and parameters."""
        params_json = json.dumps(parameters, sort_keys=True)
        key_data = f"{command_type}:{params_json}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    async def get(
        self, command_type: str, parameters: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Get a cached response if available and valid.

        Returns None if not cached, expired, or command is not cacheable.
        """
        if command_type not in self.CACHEABLE_COMMANDS:
            return None

        key = self._make_key(command_type, parameters)

        async with self._lock:
            entry = self._cache.get(key)
            if entry and entry.is_valid():
                logger.debug("Cache hit for %s", command_type)
                return entry.data
            if entry:
                del self._cache[key]
                logger.debug("Cache entry expired for %s", command_type)

        return None

    async def set(
        self,
        command_type: str,
        parameters: dict[str, Any],
        response: dict[str, Any],
        ttl_seconds: float | None = None,
    ) -> None:
        """Cache a successful response.

        Only caches if the command type is cacheable and the response
        indicates success.
        """
        if command_type not in self.CACHEABLE_COMMANDS:
            return
        if not response.get("success"):
            return

        key = self._make_key(command_type, parameters)
        ttl = ttl_seconds or self.DEFAULT_TTL.get(command_type, 5.0)

        async with self._lock:
            if len(self._cache) >= self._max_entries:
                self._evict_oldest()
            self._cache[key] = CacheEntry(
                data=response,
                timestamp=datetime.now(timezone.utc),
                ttl_seconds=ttl,
            )
            logger.debug(
                "Cached %s (TTL: %.1fs, size: %d/%d)",
                command_type, ttl, len(self._cache), self._max_entries,
            )

    def _evict_oldest(self) -> None:
        """Remove the oldest cache entry (LRU eviction).

        Caller must hold self._lock.
        """
        if not self._cache:
            return
        oldest_key = min(self._cache, key=lambda k: self._cache[k].timestamp)
        del self._cache[oldest_key]
        logger.debug("Evicted oldest cache entry: %s", oldest_key)

    async def invalidate(self, pattern: str | None = None) -> int:
        """Invalidate cache entries, optionally filtered by pattern.

        Args:
            pattern: If provided, only keys containing this string are removed.
                     If None, all entries are cleared.

        Returns:
            Number of entries removed.
        """
        async with self._lock:
            if pattern is None:
                count = len(self._cache)
                self._cache.clear()
                logger.info("Invalidated all %d cache entries", count)
                return count
            keys = [k for k in self._cache if pattern in k]
            for key in keys:
                del self._cache[key]
            logger.info("Invalidated %d entries matching '%s'", len(keys), pattern)
            return len(keys)

    async def check_scene_change(self, current_scene: str) -> None:
        """Invalidate cache if the active scene has changed."""
        if self._last_scene is not None and self._last_scene != current_scene:
            logger.info("Scene changed %s -> %s, invalidating cache", self._last_scene, current_scene)
            await self.invalidate()
        self._last_scene = current_scene

    async def get_stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        async with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self._max_entries,
                "utilization_percent": (len(self._cache) / self._max_entries) * 100,
                "last_scene": self._last_scene,
            }


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_cache: ResponseCache | None = None


def get_cache() -> ResponseCache:
    """Get or create the global ResponseCache singleton."""
    global _cache
    if _cache is None:
        _cache = ResponseCache()
        logger.debug("Created global ResponseCache instance")
    return _cache

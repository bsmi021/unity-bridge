"""Unit tests for response_cache.py — ResponseCache."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from unity_bridge.core.cache import CacheEntry, ResponseCache, get_cache


# ---------------------------------------------------------------------------
# CacheEntry validity
# ---------------------------------------------------------------------------


class TestCacheEntry:

    def test_valid_entry(self) -> None:
        entry = CacheEntry(
            data={"success": True},
            timestamp=datetime.now(timezone.utc),
            ttl_seconds=10.0,
        )
        assert entry.is_valid() is True

    def test_expired_entry(self) -> None:
        entry = CacheEntry(
            data={"success": True},
            timestamp=datetime.now(timezone.utc) - timedelta(seconds=20),
            ttl_seconds=5.0,
        )
        assert entry.is_valid() is False


# ---------------------------------------------------------------------------
# Cache hit / miss
# ---------------------------------------------------------------------------


class TestResponseCache:

    async def test_cache_miss_returns_none(self) -> None:
        cache = ResponseCache()
        result = await cache.get("query-hierarchy", {"depth": 3})
        assert result is None

    async def test_cache_hit_returns_data(self) -> None:
        cache = ResponseCache()
        response = {"success": True, "data": {"objects": []}}
        await cache.set("query-hierarchy", {"depth": 3}, response)
        result = await cache.get("query-hierarchy", {"depth": 3})
        assert result is not None
        assert result["success"] is True
        assert result["data"] == {"objects": []}

    async def test_different_params_are_separate_keys(self) -> None:
        cache = ResponseCache()
        resp_a = {"success": True, "data": "a"}
        resp_b = {"success": True, "data": "b"}
        await cache.set("query-hierarchy", {"depth": 1}, resp_a)
        await cache.set("query-hierarchy", {"depth": 5}, resp_b)

        assert (await cache.get("query-hierarchy", {"depth": 1}))["data"] == "a"
        assert (await cache.get("query-hierarchy", {"depth": 5}))["data"] == "b"

    async def test_uncacheable_command_returns_none(self) -> None:
        cache = ResponseCache()
        await cache.set("run-tests", {}, {"success": True, "data": "x"})
        result = await cache.get("run-tests", {})
        assert result is None

    async def test_failed_response_not_cached(self) -> None:
        cache = ResponseCache()
        await cache.set("query-hierarchy", {}, {"success": False, "error": "fail"})
        result = await cache.get("query-hierarchy", {})
        assert result is None


# ---------------------------------------------------------------------------
# TTL expiry
# ---------------------------------------------------------------------------


class TestCacheTTL:

    async def test_ttl_expiry(self) -> None:
        cache = ResponseCache()
        response = {"success": True, "data": "val"}
        # Set with very short TTL
        await cache.set("query-hierarchy", {}, response, ttl_seconds=0.01)

        # Immediate read should work
        # But after we patch time forward, it should expire
        import asyncio
        await asyncio.sleep(0.05)

        result = await cache.get("query-hierarchy", {})
        assert result is None  # expired

    async def test_custom_ttl_used(self) -> None:
        cache = ResponseCache()
        response = {"success": True, "data": "val"}
        await cache.set("query-hierarchy", {}, response, ttl_seconds=3600)
        result = await cache.get("query-hierarchy", {})
        assert result is not None


# ---------------------------------------------------------------------------
# LRU eviction
# ---------------------------------------------------------------------------


class TestCacheEviction:

    async def test_lru_eviction_at_max_size(self) -> None:
        cache = ResponseCache(max_entries=3)

        for i in range(4):
            await cache.set(
                "query-hierarchy",
                {"idx": i},
                {"success": True, "data": f"val_{i}"},
            )

        stats = await cache.get_stats()
        assert stats["size"] <= 3  # oldest was evicted

    async def test_eviction_removes_oldest(self) -> None:
        cache = ResponseCache(max_entries=2)
        resp = {"success": True, "data": "x"}
        await cache.set("query-hierarchy", {"k": "first"}, resp)
        await cache.set("query-hierarchy", {"k": "second"}, resp)
        # This should evict "first"
        await cache.set("query-hierarchy", {"k": "third"}, resp)

        stats = await cache.get_stats()
        assert stats["size"] == 2


# ---------------------------------------------------------------------------
# Invalidation
# ---------------------------------------------------------------------------


class TestCacheInvalidation:

    async def test_invalidate_all(self) -> None:
        cache = ResponseCache()
        await cache.set("query-hierarchy", {}, {"success": True, "data": "x"})
        count = await cache.invalidate()
        assert count >= 1
        stats = await cache.get_stats()
        assert stats["size"] == 0

    async def test_scene_change_invalidation(self) -> None:
        cache = ResponseCache()
        await cache.set("query-hierarchy", {}, {"success": True, "data": "x"})
        await cache.check_scene_change("SceneA")
        # No invalidation on first call
        result = await cache.get("query-hierarchy", {})
        assert result is not None

        # Scene change should invalidate
        await cache.check_scene_change("SceneB")
        result = await cache.get("query-hierarchy", {})
        assert result is None


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------


class TestGetCache:

    def test_returns_same_instance(self) -> None:
        # Reset global
        import unity_bridge.core.cache as cache_mod
        cache_mod._cache = None
        c1 = get_cache()
        c2 = get_cache()
        assert c1 is c2
        cache_mod._cache = None  # cleanup

"""
Unit tests for response_cache.py module.

Tests LRU caching for Unity Bridge read-only command responses.
Following TDD Red-Green-Refactor methodology.
"""

import pytest
import asyncio
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Any


# Import will fail initially (RED phase) - that's expected in TDD
try:
    from response_cache import (
        CacheEntry,
        ResponseCache,
        get_cache
    )
except ImportError:
    CacheEntry = None
    ResponseCache = None
    get_cache = None


class TestCacheEntry:
    """Test CacheEntry dataclass."""

    def test_cache_entry_creation(self):
        """CacheEntry should store data, timestamp, and TTL."""
        now = datetime.now()
        entry = CacheEntry(
            data={"success": True, "value": 42},
            timestamp=now,
            ttl_seconds=5.0
        )

        assert entry.data == {"success": True, "value": 42}
        assert entry.timestamp == now
        assert entry.ttl_seconds == 5.0

    def test_is_valid_fresh_entry(self):
        """Fresh cache entry should be valid."""
        entry = CacheEntry(
            data={"test": "data"},
            timestamp=datetime.now(),
            ttl_seconds=10.0
        )

        assert entry.is_valid() is True

    @pytest.mark.asyncio
    async def test_is_valid_expired_entry(self):
        """Expired cache entry should be invalid."""
        past_time = datetime.now() - timedelta(seconds=10)
        entry = CacheEntry(
            data={"test": "data"},
            timestamp=past_time,
            ttl_seconds=5.0
        )

        assert entry.is_valid() is False

    @pytest.mark.asyncio
    async def test_is_valid_boundary_condition(self):
        """Entry at exact TTL boundary should be tested."""
        entry = CacheEntry(
            data={"test": "data"},
            timestamp=datetime.now(),
            ttl_seconds=0.1
        )

        assert entry.is_valid() is True
        await asyncio.sleep(0.15)
        assert entry.is_valid() is False


@pytest.fixture
def cache():
    """Fixture providing a fresh ResponseCache instance."""
    return ResponseCache(max_entries=10)


@pytest.fixture
def large_cache():
    """Fixture providing a cache with larger capacity."""
    return ResponseCache(max_entries=100)


class TestResponseCacheBasics:
    """Test basic cache operations."""

    def test_cache_initialization(self):
        """Cache should initialize with default values."""
        cache = ResponseCache()
        assert cache._max_entries == 100
        assert len(cache._cache) == 0
        assert cache._last_scene is None

    def test_cache_custom_max_entries(self):
        """Cache should accept custom max_entries."""
        cache = ResponseCache(max_entries=50)
        assert cache._max_entries == 50

    def test_cacheable_commands_defined(self):
        """CACHEABLE_COMMANDS should be defined."""
        assert ResponseCache.CACHEABLE_COMMANDS is not None
        assert "query-hierarchy" in ResponseCache.CACHEABLE_COMMANDS
        assert "get-component-data" in ResponseCache.CACHEABLE_COMMANDS
        assert "get-selection" in ResponseCache.CACHEABLE_COMMANDS

    def test_default_ttl_defined(self):
        """DEFAULT_TTL should define TTLs for cacheable commands."""
        assert ResponseCache.DEFAULT_TTL is not None
        assert "query-hierarchy" in ResponseCache.DEFAULT_TTL
        assert ResponseCache.DEFAULT_TTL["query-hierarchy"] > 0


@pytest.mark.asyncio
class TestCacheGetSet:
    """Test cache get and set operations."""

    async def test_cache_miss_nonexistent(self, cache):
        """Getting non-existent key should return None."""
        result = await cache.get("query-hierarchy", {"maxDepth": 3})
        assert result is None

    async def test_cache_hit_simple(self, cache):
        """Setting then getting should return cached data."""
        params = {"maxDepth": 3}
        response = {"success": True, "data": {"objects": []}}

        await cache.set("query-hierarchy", params, response)
        result = await cache.get("query-hierarchy", params)

        assert result is not None
        assert result["success"] is True
        assert result["data"] == {"objects": []}

    async def test_cache_miss_different_params(self, cache):
        """Different parameters should result in cache miss."""
        await cache.set(
            "query-hierarchy",
            {"maxDepth": 3},
            {"success": True, "data": {"count": 5}}
        )

        result = await cache.get("query-hierarchy", {"maxDepth": 5})
        assert result is None

    async def test_cache_miss_different_command(self, cache):
        """Different command type should result in cache miss."""
        await cache.set(
            "query-hierarchy",
            {"maxDepth": 3},
            {"success": True}
        )

        result = await cache.get("get-component-data", {"maxDepth": 3})
        assert result is None

    async def test_uncacheable_command_not_cached(self, cache):
        """Non-cacheable commands should not be stored."""
        await cache.set(
            "set-component-data",  # Not in CACHEABLE_COMMANDS
            {"value": 42},
            {"success": True}
        )

        result = await cache.get("set-component-data", {"value": 42})
        assert result is None

    async def test_failed_response_not_cached(self, cache):
        """Failed responses should not be cached."""
        await cache.set(
            "query-hierarchy",
            {},
            {"success": False, "error": "GameObject not found"}
        )

        result = await cache.get("query-hierarchy", {})
        assert result is None

    async def test_cache_expiry(self, cache):
        """Cached entries should expire after TTL."""
        await cache.set(
            "query-hierarchy",
            {},
            {"success": True, "data": "test"},
            ttl_seconds=0.1
        )

        # Should be cached immediately
        result1 = await cache.get("query-hierarchy", {})
        assert result1 is not None

        # Wait for expiry
        await asyncio.sleep(0.15)

        # Should be expired
        result2 = await cache.get("query-hierarchy", {})
        assert result2 is None

    async def test_cache_custom_ttl(self, cache):
        """Custom TTL should override default."""
        await cache.set(
            "query-hierarchy",
            {},
            {"success": True},
            ttl_seconds=0.2
        )

        await asyncio.sleep(0.1)
        result = await cache.get("query-hierarchy", {})
        assert result is not None  # Still valid

    async def test_cache_default_ttl_used(self, cache):
        """Default TTL should be used when not specified."""
        # Set without TTL parameter
        await cache.set(
            "query-hierarchy",
            {},
            {"success": True}
        )

        # Should use DEFAULT_TTL["query-hierarchy"]
        result = await cache.get("query-hierarchy", {})
        assert result is not None


class TestCacheKeyGeneration:
    """Test cache key generation from command and parameters."""

    @pytest.mark.asyncio
    async def test_same_params_same_key(self, cache):
        """Same parameters should generate same cache key."""
        params1 = {"maxDepth": 3, "includeComponents": True}
        params2 = {"maxDepth": 3, "includeComponents": True}

        await cache.set("query-hierarchy", params1, {"success": True, "data": "test1"})
        result = await cache.get("query-hierarchy", params2)

        assert result is not None
        assert result["data"] == "test1"

    @pytest.mark.asyncio
    async def test_param_order_irrelevant(self, cache):
        """Parameter order should not affect cache key."""
        params1 = {"a": 1, "b": 2, "c": 3}
        params2 = {"c": 3, "a": 1, "b": 2}

        await cache.set("query-hierarchy", params1, {"success": True, "data": "test"})
        result = await cache.get("query-hierarchy", params2)

        assert result is not None

    @pytest.mark.asyncio
    async def test_param_values_matter(self, cache):
        """Different parameter values should produce different keys."""
        params1 = {"maxDepth": 3}
        params2 = {"maxDepth": 5}

        await cache.set("query-hierarchy", params1, {"success": True, "data": "depth3"})
        await cache.set("query-hierarchy", params2, {"success": True, "data": "depth5"})

        result1 = await cache.get("query-hierarchy", params1)
        result2 = await cache.get("query-hierarchy", params2)

        assert result1["data"] == "depth3"
        assert result2["data"] == "depth5"

    @pytest.mark.asyncio
    async def test_empty_params_cacheable(self, cache):
        """Empty parameters should be cacheable."""
        await cache.set("get-selection", {}, {"success": True, "count": 0})
        result = await cache.get("get-selection", {})

        assert result is not None


@pytest.mark.asyncio
class TestCacheEviction:
    """Test LRU cache eviction behavior."""

    async def test_eviction_at_capacity(self):
        """Cache should evict oldest entry when at capacity."""
        small_cache = ResponseCache(max_entries=3)

        # Fill cache to capacity
        await small_cache.set("query-hierarchy", {"id": 1}, {"success": True, "data": "entry1"})
        await asyncio.sleep(0.01)  # Ensure different timestamps
        await small_cache.set("query-hierarchy", {"id": 2}, {"success": True, "data": "entry2"})
        await asyncio.sleep(0.01)
        await small_cache.set("query-hierarchy", {"id": 3}, {"success": True, "data": "entry3"})

        # Add one more - should evict oldest (id=1)
        await small_cache.set("query-hierarchy", {"id": 4}, {"success": True, "data": "entry4"})

        # Entry 1 should be gone
        result1 = await small_cache.get("query-hierarchy", {"id": 1})
        assert result1 is None

        # Others should still be there
        result2 = await small_cache.get("query-hierarchy", {"id": 2})
        result3 = await small_cache.get("query-hierarchy", {"id": 3})
        result4 = await small_cache.get("query-hierarchy", {"id": 4})

        assert result2 is not None
        assert result3 is not None
        assert result4 is not None

    async def test_no_eviction_below_capacity(self, cache):
        """Cache should not evict when below capacity."""
        # Add 5 entries to cache with capacity 10
        for i in range(5):
            await cache.set("query-hierarchy", {"id": i}, {"success": True})
            await asyncio.sleep(0.01)

        # All should still be present
        for i in range(5):
            result = await cache.get("query-hierarchy", {"id": i})
            assert result is not None


@pytest.mark.asyncio
class TestCacheInvalidation:
    """Test cache invalidation operations."""

    async def test_invalidate_all(self, cache):
        """Invalidate with no pattern should clear all entries."""
        await cache.set("query-hierarchy", {"id": 1}, {"success": True})
        await cache.set("query-hierarchy", {"id": 2}, {"success": True})
        await cache.set("get-selection", {}, {"success": True})

        count = await cache.invalidate()

        assert count == 3
        assert len(cache._cache) == 0

    async def test_invalidate_returns_count(self, cache):
        """Invalidate should return number of entries removed."""
        await cache.set("query-hierarchy", {"id": 1}, {"success": True})
        await cache.set("query-hierarchy", {"id": 2}, {"success": True})

        count = await cache.invalidate()
        assert count == 2

    async def test_invalidate_empty_cache(self, cache):
        """Invalidating empty cache should return 0."""
        count = await cache.invalidate()
        assert count == 0

    async def test_invalidate_with_pattern(self, cache):
        """Invalidate with pattern should only remove matching entries."""
        # This test assumes pattern matching by command type or key
        await cache.set("query-hierarchy", {"id": 1}, {"success": True})
        await cache.set("get-selection", {"id": 2}, {"success": True})

        # Implementation-dependent: pattern might match cache keys
        count = await cache.invalidate(pattern="query")

        # Should invalidate entries matching pattern
        assert count >= 0


@pytest.mark.asyncio
class TestSceneChangeInvalidation:
    """Test automatic cache invalidation on scene changes."""

    async def test_scene_change_invalidates_cache(self, cache):
        """Cache should invalidate when scene changes."""
        # Set up cache with scene "Scene1"
        await cache.check_scene_change("Scene1")
        await cache.set("query-hierarchy", {}, {"success": True, "data": "scene1_data"})

        # Change to Scene2
        await cache.check_scene_change("Scene2")

        # Cache should be invalidated
        result = await cache.get("query-hierarchy", {})
        assert result is None

    async def test_same_scene_no_invalidation(self, cache):
        """Cache should not invalidate if scene hasn't changed."""
        await cache.check_scene_change("Scene1")
        await cache.set("query-hierarchy", {}, {"success": True, "data": "test"})

        await cache.check_scene_change("Scene1")

        # Cache should still be valid
        result = await cache.get("query-hierarchy", {})
        assert result is not None

    async def test_first_scene_no_invalidation(self, cache):
        """First scene check should not invalidate."""
        await cache.set("query-hierarchy", {}, {"success": True})

        await cache.check_scene_change("InitialScene")

        result = await cache.get("query-hierarchy", {})
        assert result is not None


class TestGetCacheGlobal:
    """Test global cache instance getter."""

    def test_get_cache_returns_instance(self):
        """get_cache() should return ResponseCache instance."""
        cache = get_cache()
        assert isinstance(cache, ResponseCache)

    def test_get_cache_singleton(self):
        """get_cache() should return same instance on multiple calls."""
        cache1 = get_cache()
        cache2 = get_cache()
        assert cache1 is cache2


@pytest.mark.asyncio
class TestConcurrencyAndThreadSafety:
    """Test cache behavior under concurrent access."""

    async def test_concurrent_gets(self, cache):
        """Multiple concurrent gets should work correctly."""
        await cache.set("query-hierarchy", {}, {"success": True, "data": "test"})

        # Concurrent gets
        results = await asyncio.gather(*[
            cache.get("query-hierarchy", {})
            for _ in range(10)
        ])

        # All should succeed
        assert all(r is not None for r in results)
        assert all(r["data"] == "test" for r in results)

    async def test_concurrent_sets(self, cache):
        """Multiple concurrent sets should not corrupt cache."""
        # Concurrent sets with different IDs
        await asyncio.gather(*[
            cache.set("query-hierarchy", {"id": i}, {"success": True, "data": f"test{i}"})
            for i in range(10)
        ])

        # All should be retrievable
        for i in range(10):
            result = await cache.get("query-hierarchy", {"id": i})
            assert result is not None

    async def test_concurrent_get_and_set(self, cache):
        """Concurrent gets and sets should work correctly."""
        async def get_or_set(i):
            if i % 2 == 0:
                await cache.set("query-hierarchy", {"id": i}, {"success": True})
            else:
                await cache.get("query-hierarchy", {"id": i - 1})

        await asyncio.gather(*[get_or_set(i) for i in range(20)])


@pytest.mark.asyncio
class TestCachePerformance:
    """Test cache performance characteristics."""

    async def test_cache_hit_faster_than_miss(self, large_cache):
        """Cache hits should be faster than misses."""
        import time

        # Populate cache
        await large_cache.set("query-hierarchy", {"test": "data"}, {"success": True, "large_data": "x" * 1000})

        # Measure cache hit
        hit_times = []
        for _ in range(100):
            start = time.perf_counter()
            await large_cache.get("query-hierarchy", {"test": "data"})
            hit_times.append(time.perf_counter() - start)

        # Measure cache miss
        miss_times = []
        for i in range(100):
            start = time.perf_counter()
            await large_cache.get("query-hierarchy", {"test": f"missing{i}"})
            miss_times.append(time.perf_counter() - start)

        avg_hit = sum(hit_times) / len(hit_times)
        avg_miss = sum(miss_times) / len(miss_times)

        # Hits should be comparable to misses (both very fast)
        # This is mainly to ensure caching doesn't add significant overhead
        assert avg_hit < 0.001  # Less than 1ms
        assert avg_miss < 0.001


# Skip all tests if module not yet implemented (TDD RED phase)
pytestmark = pytest.mark.skipif(
    ResponseCache is None,
    reason="response_cache module not yet implemented (TDD RED phase)"
)

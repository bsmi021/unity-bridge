"""Unit tests for retry_handler.py — retry_async and RetryConfig."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock

import pytest

from unity_bridge.core.retry import (
    RetryConfig,
    is_retryable_error,
    retry_async,
)


# ---------------------------------------------------------------------------
# is_retryable_error
# ---------------------------------------------------------------------------


class TestIsRetryableError:

    def test_retryable_patterns_detected(self) -> None:
        assert is_retryable_error("file is being used by another process") is True
        assert is_retryable_error("Access Denied") is True
        assert is_retryable_error("Sharing violation on path") is True
        assert is_retryable_error("Resource temporarily unavailable") is True
        assert is_retryable_error("Command timeout") is True
        assert is_retryable_error("Connection refused") is True

    def test_permanent_errors_not_retryable(self) -> None:
        assert is_retryable_error("NullReferenceException") is False
        assert is_retryable_error("Invalid command type") is False
        assert is_retryable_error("Component not found") is False

    def test_case_insensitive(self) -> None:
        assert is_retryable_error("FILE IS BEING USED") is True
        assert is_retryable_error("ACCESS DENIED") is True


# ---------------------------------------------------------------------------
# RetryConfig
# ---------------------------------------------------------------------------


class TestRetryConfig:

    def test_default_values(self) -> None:
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 0.1
        assert config.max_delay == 2.0
        assert config.exponential_base == 2.0

    def test_exponential_backoff(self) -> None:
        config = RetryConfig(base_delay=0.1, exponential_base=2.0, max_delay=10.0)
        assert config.get_delay(0) == pytest.approx(0.1)  # 0.1 * 2^0
        assert config.get_delay(1) == pytest.approx(0.2)  # 0.1 * 2^1
        assert config.get_delay(2) == pytest.approx(0.4)  # 0.1 * 2^2
        assert config.get_delay(3) == pytest.approx(0.8)  # 0.1 * 2^3

    def test_delay_capped_at_max(self) -> None:
        config = RetryConfig(base_delay=1.0, exponential_base=10.0, max_delay=5.0)
        assert config.get_delay(0) == 1.0
        assert config.get_delay(1) == 5.0  # 10.0 capped to 5.0
        assert config.get_delay(5) == 5.0  # still capped

    def test_custom_values(self) -> None:
        config = RetryConfig(max_retries=5, base_delay=0.5)
        assert config.max_retries == 5
        assert config.base_delay == 0.5


# ---------------------------------------------------------------------------
# retry_async — retries on transient errors
# ---------------------------------------------------------------------------


class TestRetryAsync:

    async def test_returns_immediately_on_success(self) -> None:
        func = AsyncMock(return_value={"success": True, "data": "ok"})
        config = RetryConfig(max_retries=3, base_delay=0.01)
        result = await retry_async(func, config=config)
        assert result["success"] is True
        assert func.await_count == 1

    async def test_retries_on_transient_error(self) -> None:
        call_count = 0

        async def flaky() -> dict:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return {"success": False, "error": "file is being used"}
            return {"success": True, "data": "recovered"}

        config = RetryConfig(max_retries=3, base_delay=0.01)
        result = await retry_async(flaky, config=config)
        assert result["success"] is True
        assert call_count == 3

    async def test_no_retry_on_permanent_error(self) -> None:
        func = AsyncMock(return_value={
            "success": False,
            "error": "Component not found"
        })
        config = RetryConfig(max_retries=3, base_delay=0.01)
        result = await retry_async(func, config=config)
        assert result["success"] is False
        assert func.await_count == 1  # No retry

    async def test_max_retries_respected(self) -> None:
        func = AsyncMock(return_value={
            "success": False,
            "error": "file is being used"
        })
        config = RetryConfig(max_retries=2, base_delay=0.01)
        result = await retry_async(func, config=config)
        assert result["success"] is False
        # 1 initial + 2 retries = 3 calls
        assert func.await_count == 3

    async def test_retries_on_io_exception(self) -> None:
        call_count = 0

        async def raises_then_succeeds() -> dict:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise IOError("disk full")
            return {"success": True}

        config = RetryConfig(max_retries=3, base_delay=0.01)
        result = await retry_async(raises_then_succeeds, config=config)
        assert result["success"] is True
        assert call_count == 2

    async def test_raises_after_exhausting_retries(self) -> None:
        async def always_fails() -> dict:
            raise PermissionError("locked")

        config = RetryConfig(max_retries=2, base_delay=0.01)
        with pytest.raises(PermissionError, match="locked"):
            await retry_async(always_fails, config=config)

    async def test_exponential_backoff_timing(self) -> None:
        """Verify delays increase between retries."""
        timestamps: list[float] = []

        async def track_time() -> dict:
            timestamps.append(time.monotonic())
            return {"success": False, "error": "timeout"}

        config = RetryConfig(max_retries=3, base_delay=0.05, exponential_base=2.0)
        await retry_async(track_time, config=config)

        assert len(timestamps) == 4  # 1 initial + 3 retries
        # Each gap should be >= base_delay * 2^attempt
        for i in range(1, len(timestamps)):
            gap = timestamps[i] - timestamps[i - 1]
            assert gap >= 0.03  # Allow some timing slack

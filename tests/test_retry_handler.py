"""
Unit tests for retry_handler.py module.

Tests retry logic with exponential backoff for Unity Bridge commands.
Following TDD Red-Green-Refactor methodology.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from typing import Dict, Any


# Import will fail initially (RED phase) - that's expected in TDD
try:
    from retry_handler import (
        RetryConfig,
        retry_async,
        is_retryable_error,
        with_retry,
        RETRYABLE_ERROR_PATTERNS,
        DEFAULT_RETRY_CONFIG
    )
except ImportError:
    # Placeholder for when module doesn't exist yet
    RetryConfig = None
    retry_async = None
    is_retryable_error = None
    with_retry = None
    RETRYABLE_ERROR_PATTERNS = None
    DEFAULT_RETRY_CONFIG = None


class TestIsRetryableError:
    """Test error classification for retry logic."""

    def test_file_in_use_error(self):
        """File in use errors should be retryable."""
        assert is_retryable_error("file is being used by another process")
        assert is_retryable_error("The file is being used")

    def test_access_denied_error(self):
        """Access denied errors should be retryable."""
        assert is_retryable_error("access denied")
        assert is_retryable_error("Access Denied")

    def test_sharing_violation_error(self):
        """Sharing violation errors should be retryable."""
        assert is_retryable_error("sharing violation")
        assert is_retryable_error("Sharing Violation occurred")

    def test_timeout_error(self):
        """Timeout errors should be retryable."""
        assert is_retryable_error("timeout occurred")
        assert is_retryable_error("Connection timeout")

    def test_temporarily_unavailable_error(self):
        """Temporarily unavailable errors should be retryable."""
        assert is_retryable_error("temporarily unavailable")
        assert is_retryable_error("Resource temporarily unavailable")

    def test_process_access_error(self):
        """Process access errors should be retryable."""
        assert is_retryable_error("process cannot access the file")

    def test_connection_refused_error(self):
        """Connection refused errors should be retryable."""
        assert is_retryable_error("connection refused")

    def test_non_retryable_gameobject_error(self):
        """GameObject not found errors should NOT be retryable."""
        assert not is_retryable_error("GameObject not found")

    def test_non_retryable_invalid_parameter(self):
        """Invalid parameter errors should NOT be retryable."""
        assert not is_retryable_error("Invalid parameter")

    def test_non_retryable_null_reference(self):
        """Null reference errors should NOT be retryable."""
        assert not is_retryable_error("NullReferenceException")

    def test_case_insensitive_matching(self):
        """Error pattern matching should be case-insensitive."""
        assert is_retryable_error("ACCESS DENIED")
        assert is_retryable_error("File Is Being Used")
        assert is_retryable_error("TIMEOUT")

    def test_empty_string(self):
        """Empty error strings should not be retryable."""
        assert not is_retryable_error("")

    def test_pattern_in_middle_of_string(self):
        """Pattern matching should work anywhere in error string."""
        assert is_retryable_error("Error: file is being used, please try again")
        assert is_retryable_error("System.IO.IOException: sharing violation at line 42")


class TestRetryConfig:
    """Test RetryConfig configuration class."""

    def test_default_values(self):
        """RetryConfig should have sensible defaults."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 0.1
        assert config.max_delay == 2.0
        assert config.exponential_base == 2.0

    def test_custom_values(self):
        """RetryConfig should accept custom values."""
        config = RetryConfig(
            max_retries=5,
            base_delay=0.5,
            max_delay=10.0,
            exponential_base=3.0
        )
        assert config.max_retries == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 10.0
        assert config.exponential_base == 3.0

    def test_get_delay_first_attempt(self):
        """First retry delay should be base_delay."""
        config = RetryConfig(base_delay=0.2, exponential_base=2.0)
        # Attempt 0 is first retry
        assert config.get_delay(0) == 0.2

    def test_get_delay_exponential_growth(self):
        """Delay should grow exponentially."""
        config = RetryConfig(base_delay=0.1, exponential_base=2.0, max_delay=10.0)
        # Attempt 0: 0.1 * 2^0 = 0.1
        assert config.get_delay(0) == 0.1
        # Attempt 1: 0.1 * 2^1 = 0.2
        assert config.get_delay(1) == 0.2
        # Attempt 2: 0.1 * 2^2 = 0.4
        assert config.get_delay(2) == 0.4
        # Attempt 3: 0.1 * 2^3 = 0.8
        assert config.get_delay(3) == 0.8

    def test_get_delay_respects_max_delay(self):
        """Delay should not exceed max_delay."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, max_delay=5.0)
        # Attempt 5: 1.0 * 2^5 = 32.0, but capped at 5.0
        assert config.get_delay(5) == 5.0
        assert config.get_delay(10) == 5.0

    def test_get_delay_with_different_base(self):
        """Different exponential bases should produce different delays."""
        config_base2 = RetryConfig(base_delay=0.1, exponential_base=2.0, max_delay=10.0)
        config_base3 = RetryConfig(base_delay=0.1, exponential_base=3.0, max_delay=10.0)

        # Both start the same
        assert config_base2.get_delay(0) == config_base3.get_delay(0)

        # But grow at different rates
        # base 2: 0.1 * 2^2 = 0.4
        # base 3: 0.1 * 3^2 = 0.9
        assert config_base2.get_delay(2) < config_base3.get_delay(2)


@pytest.mark.asyncio
class TestRetryAsync:
    """Test async retry function."""

    async def test_success_first_attempt(self):
        """Function succeeding on first attempt should not retry."""
        call_count = 0

        async def succeed():
            nonlocal call_count
            call_count += 1
            return {"success": True, "data": "ok"}

        result = await retry_async(succeed)

        assert result["success"] is True
        assert result["data"] == "ok"
        assert call_count == 1

    async def test_success_after_two_failures(self):
        """Function should succeed after transient failures."""
        call_count = 0

        async def fail_twice_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return {"success": False, "error": "file is being used"}
            return {"success": True, "data": "finally worked"}

        config = RetryConfig(max_retries=3, base_delay=0.01, max_delay=0.1)
        result = await retry_async(fail_twice_then_succeed, config=config)

        assert result["success"] is True
        assert result["data"] == "finally worked"
        assert call_count == 3

    async def test_non_retryable_error_no_retry(self):
        """Non-retryable errors should return immediately without retry."""
        call_count = 0

        async def fail_non_retryable():
            nonlocal call_count
            call_count += 1
            return {"success": False, "error": "GameObject not found"}

        config = RetryConfig(max_retries=3, base_delay=0.01)
        result = await retry_async(fail_non_retryable, config=config)

        assert result["success"] is False
        assert "GameObject not found" in result["error"]
        assert call_count == 1  # No retries

    async def test_max_retries_exhausted(self):
        """Should give up after max_retries attempts."""
        call_count = 0

        async def always_fail_retryable():
            nonlocal call_count
            call_count += 1
            return {"success": False, "error": "timeout occurred"}

        config = RetryConfig(max_retries=2, base_delay=0.01)
        result = await retry_async(always_fail_retryable, config=config)

        assert result["success"] is False
        assert "timeout" in result["error"]
        assert call_count == 3  # Initial + 2 retries

    async def test_exception_retry_behavior(self):
        """IOError/PermissionError/OSError should trigger retry."""
        call_count = 0

        async def raise_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise PermissionError("Access denied")
            return {"success": True, "data": "recovered"}

        config = RetryConfig(max_retries=3, base_delay=0.01)
        result = await retry_async(raise_then_succeed, config=config)

        assert result["success"] is True
        assert call_count == 3

    async def test_exception_max_retries_exceeded(self):
        """Should raise exception if retries exhausted."""
        call_count = 0

        async def always_raise():
            nonlocal call_count
            call_count += 1
            raise IOError("File locked")

        config = RetryConfig(max_retries=2, base_delay=0.01)

        with pytest.raises(IOError, match="File locked"):
            await retry_async(always_raise, config=config)

        assert call_count == 3

    async def test_exponential_backoff_timing(self):
        """Verify exponential backoff timing is approximately correct."""
        call_times = []

        async def record_time():
            call_times.append(asyncio.get_event_loop().time())
            if len(call_times) < 3:
                return {"success": False, "error": "timeout"}
            return {"success": True}

        config = RetryConfig(max_retries=3, base_delay=0.1, exponential_base=2.0)
        await retry_async(record_time, config=config)

        # Check delays between calls
        assert len(call_times) == 3

        # First delay: ~0.1s (base_delay * 2^0)
        delay1 = call_times[1] - call_times[0]
        assert 0.08 < delay1 < 0.15

        # Second delay: ~0.2s (base_delay * 2^1)
        delay2 = call_times[2] - call_times[1]
        assert 0.18 < delay2 < 0.25

    async def test_default_config_used(self):
        """Should use DEFAULT_RETRY_CONFIG when config=None."""
        call_count = 0

        async def fail_once():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"success": False, "error": "access denied"}
            return {"success": True}

        # No config parameter
        result = await retry_async(fail_once)

        assert result["success"] is True
        assert call_count == 2

    async def test_function_with_args(self):
        """Should pass args and kwargs to function."""
        async def add(a, b, multiplier=1):
            return {"success": True, "result": (a + b) * multiplier}

        result = await retry_async(add, 5, 3, multiplier=2)

        assert result["success"] is True
        assert result["result"] == 16

    async def test_non_dict_return_value(self):
        """Should handle non-dict return values."""
        async def return_string():
            return "simple string"

        result = await retry_async(return_string)

        assert result == "simple string"


@pytest.mark.asyncio
class TestWithRetryDecorator:
    """Test with_retry decorator."""

    async def test_decorator_basic_usage(self):
        """Decorator should add retry logic to function."""
        call_count = 0

        @with_retry()
        async def my_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return {"success": False, "error": "timeout"}
            return {"success": True}

        result = await my_function()

        assert result["success"] is True
        assert call_count == 2

    async def test_decorator_custom_config(self):
        """Decorator should accept custom RetryConfig."""
        call_count = 0

        @with_retry(RetryConfig(max_retries=5, base_delay=0.01))
        async def important_function():
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                return {"success": False, "error": "sharing violation"}
            return {"success": True}

        result = await important_function()

        assert result["success"] is True
        assert call_count == 4

    async def test_decorator_preserves_function_metadata(self):
        """Decorator should preserve function name and docstring."""
        @with_retry()
        async def documented_function():
            """This is a documented function."""
            return {"success": True}

        assert documented_function.__name__ == "documented_function"
        assert "documented function" in documented_function.__doc__


class TestIntegrationScenarios:
    """Integration test scenarios combining multiple retry behaviors."""

    @pytest.mark.asyncio
    async def test_mixed_errors_scenario(self):
        """Test function with mix of retryable and non-retryable errors."""
        attempts = []

        async def complex_function():
            attempt_num = len(attempts)
            attempts.append(attempt_num)

            # Attempt 0: retryable error
            if attempt_num == 0:
                return {"success": False, "error": "timeout"}
            # Attempt 1: retryable error
            elif attempt_num == 1:
                return {"success": False, "error": "access denied"}
            # Attempt 2: success
            else:
                return {"success": True, "data": "completed"}

        config = RetryConfig(max_retries=3, base_delay=0.01)
        result = await retry_async(complex_function, config=config)

        assert result["success"] is True
        assert len(attempts) == 3

    @pytest.mark.asyncio
    async def test_file_locking_simulation(self):
        """Simulate file locking scenario common in Unity Bridge."""
        lock_released_after = 2
        call_count = 0

        async def write_file():
            nonlocal call_count
            call_count += 1

            if call_count <= lock_released_after:
                raise PermissionError("The process cannot access the file because it is being used by another process")

            return {"success": True, "written": True}

        config = RetryConfig(max_retries=3, base_delay=0.05)
        result = await retry_async(write_file, config=config)

        assert result["success"] is True
        assert call_count == 3


@pytest.fixture
def sample_retry_config():
    """Fixture providing a standard RetryConfig for tests."""
    return RetryConfig(max_retries=3, base_delay=0.01, max_delay=1.0, exponential_base=2.0)


# Skip all tests if module not yet implemented (TDD RED phase)
pytestmark = pytest.mark.skipif(
    retry_async is None,
    reason="retry_handler module not yet implemented (TDD RED phase)"
)

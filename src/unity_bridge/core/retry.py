"""
Retry handler with exponential backoff for Unity Bridge commands.

Migrated from retry_handler.py. Provides RetryConfig, retry_async,
and a decorator for automatic retries on transient failures.
"""

import asyncio
import logging
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, TypeVar

logger = logging.getLogger("unity_bridge.retry")

T = TypeVar("T")

RETRYABLE_ERROR_PATTERNS: list[str] = [
    "file is being used",
    "access denied",
    "sharing violation",
    "temporarily unavailable",
    "process cannot access",
    "timeout",
    "connection refused",
]


def is_retryable_error(error: str) -> bool:
    """Determine if an error is transient and worth retrying.

    Args:
        error: Error message string.

    Returns:
        True if the error matches a known retryable pattern.
    """
    error_lower = error.lower()
    return any(pat in error_lower for pat in RETRYABLE_ERROR_PATTERNS)


@dataclass
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay between retries in seconds.
        max_delay: Maximum delay cap in seconds.
        exponential_base: Multiplier for exponential backoff.
    """

    max_retries: int = 3
    base_delay: float = 0.1
    max_delay: float = 2.0
    exponential_base: float = 2.0

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt (0-indexed).

        Returns:
            Delay in seconds, capped at max_delay.
        """
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)


DEFAULT_RETRY_CONFIG = RetryConfig()


def _check_result_error(result: Any) -> tuple[bool, str]:
    """Extract success status and error message from a result.

    Supports CommandResult (duck-typed via 'success' attr) and legacy dicts.

    Returns:
        Tuple of (is_success, error_message). If the result type is
        unrecognized, returns (True, "") so no retry is attempted.
    """
    if hasattr(result, "success"):
        return (result.success, result.error or "")
    if isinstance(result, dict):
        return (result.get("success", True), result.get("error", ""))
    return (True, "")


async def _log_and_delay(
    cfg: RetryConfig, attempt: int, label: str, detail: str,
) -> None:
    """Log a retryable failure and sleep for the backoff delay."""
    delay = cfg.get_delay(attempt)
    logger.warning(
        "%s (attempt %d): %s. Retrying in %.2fs...",
        label, attempt + 1, detail, delay,
    )
    await asyncio.sleep(delay)


async def retry_async(
    func: Callable[..., T],
    *args: Any,
    config: RetryConfig | None = None,
    **kwargs: Any,
) -> T:
    """Execute an async function with retry logic.

    Retries when the function returns a CommandResult or dict with a
    retryable error, or raises IOError/PermissionError/OSError.

    Args:
        func: Async function to execute.
        *args: Positional arguments for func.
        config: Retry configuration (uses DEFAULT_RETRY_CONFIG if None).
        **kwargs: Keyword arguments for func.

    Returns:
        Result of func on success.

    Raises:
        Last exception if all retries are exhausted.
    """
    cfg = config or DEFAULT_RETRY_CONFIG
    last_exception: Exception | None = None
    result: Any = None

    for attempt in range(cfg.max_retries + 1):
        try:
            result = await func(*args, **kwargs)
            success, error_msg = _check_result_error(result)

            if success or not is_retryable_error(error_msg):
                return result
            if attempt < cfg.max_retries:
                await _log_and_delay(cfg, attempt, "Retryable error", error_msg)
                continue
            return result

        except (IOError, PermissionError, OSError) as exc:
            last_exception = exc
            if attempt < cfg.max_retries:
                await _log_and_delay(cfg, attempt, "Exception", str(exc))
            else:
                raise

    if last_exception:
        raise last_exception

    return result  # type: ignore[return-value]


def with_retry(config: RetryConfig | None = None) -> Callable:
    """Decorator to add retry logic to async functions.

    Usage:
        @with_retry()
        async def my_function():
            ...

        @with_retry(RetryConfig(max_retries=5))
        async def important_function():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await retry_async(func, *args, config=config, **kwargs)
        return wrapper  # type: ignore[return-value]
    return decorator

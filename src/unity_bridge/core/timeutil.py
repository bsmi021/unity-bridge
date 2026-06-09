"""Shared time / parsing helpers used across core modules.

Previously duplicated in core/health.py and core/operation.py.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def optional_int(value: Any) -> int | None:
    """Best-effort int parsing for optional values; None on failure."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_iso_datetime(timestamp_str: str) -> datetime:
    """Parse an ISO-8601 timestamp into an aware UTC datetime.

    Raises ValueError/TypeError on malformed input (callers that want a
    tolerant variant should use ``parse_optional_datetime``).
    """
    normalized = timestamp_str.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def parse_optional_datetime(value: str | None) -> datetime | None:
    """Tolerant ISO-8601 parse; returns None for empty or malformed input."""
    if not value:
        return None
    try:
        return parse_iso_datetime(value)
    except (ValueError, TypeError):
        return None


def utc_now_iso() -> str:
    """Current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()

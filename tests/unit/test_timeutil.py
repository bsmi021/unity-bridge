"""Unit tests for core/timeutil.py — shared parsing helpers."""

from __future__ import annotations

from datetime import timezone

from unity_bridge.core.timeutil import (
    optional_int,
    parse_iso_datetime,
    parse_optional_datetime,
    utc_now_iso,
)


class TestOptionalInt:
    def test_none_returns_none(self) -> None:
        assert optional_int(None) is None

    def test_valid_values(self) -> None:
        assert optional_int(5) == 5
        assert optional_int("7") == 7

    def test_garbage_returns_none(self) -> None:
        assert optional_int("abc") is None
        assert optional_int([1]) is None


class TestParseIsoDatetime:
    def test_parses_z_suffix_as_utc(self) -> None:
        dt = parse_iso_datetime("2026-01-01T00:00:00Z")
        assert dt.tzinfo is not None
        assert dt.utcoffset().total_seconds() == 0

    def test_naive_timestamp_assumed_utc(self) -> None:
        dt = parse_iso_datetime("2026-01-01T00:00:00")
        assert dt.tzinfo == timezone.utc

    def test_malformed_raises(self) -> None:
        try:
            parse_iso_datetime("not-a-date")
        except ValueError:
            return
        raise AssertionError("expected ValueError")


class TestParseOptionalDatetime:
    def test_empty_returns_none(self) -> None:
        assert parse_optional_datetime(None) is None
        assert parse_optional_datetime("") is None

    def test_malformed_returns_none(self) -> None:
        assert parse_optional_datetime("garbage") is None

    def test_valid_returns_datetime(self) -> None:
        assert parse_optional_datetime("2026-01-01T00:00:00Z") is not None


def test_utc_now_iso_is_parseable() -> None:
    assert parse_optional_datetime(utc_now_iso()) is not None

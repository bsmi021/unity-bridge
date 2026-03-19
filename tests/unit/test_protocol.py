"""Unit tests for core/protocol.py — timeout defaults and get_timeout."""

from __future__ import annotations

import pytest

from unity_bridge.core.protocol import (
    TIMEOUT_DEFAULTS,
    PARALLEL_SAFE_COMMANDS,
    get_timeout,
)


# ---------------------------------------------------------------------------
# TIMEOUT_DEFAULTS
# ---------------------------------------------------------------------------


class TestTimeoutDefaults:

    def test_known_commands_have_defaults(self) -> None:
        assert "run-tests" in TIMEOUT_DEFAULTS
        assert "compile" in TIMEOUT_DEFAULTS
        assert "query-hierarchy" in TIMEOUT_DEFAULTS
        assert "build-operation" in TIMEOUT_DEFAULTS

    def test_run_tests_timeout_is_300(self) -> None:
        assert TIMEOUT_DEFAULTS["run-tests"] == 300

    def test_compile_timeout_is_120(self) -> None:
        assert TIMEOUT_DEFAULTS["compile"] == 120

    def test_quick_commands_under_15s(self) -> None:
        quick = ["query-hierarchy", "get-component-data", "read-console", "clear-console"]
        for cmd in quick:
            if cmd in TIMEOUT_DEFAULTS:
                assert TIMEOUT_DEFAULTS[cmd] <= 15

    def test_build_operation_is_longest(self) -> None:
        assert TIMEOUT_DEFAULTS["build-operation"] == 600


# ---------------------------------------------------------------------------
# PARALLEL_SAFE_COMMANDS
# ---------------------------------------------------------------------------


class TestParallelSafeCommands:

    def test_read_only_commands_are_parallel_safe(self) -> None:
        assert "query-hierarchy" in PARALLEL_SAFE_COMMANDS
        assert "get-component-data" in PARALLEL_SAFE_COMMANDS
        assert "get-selection" in PARALLEL_SAFE_COMMANDS
        assert "read-console" in PARALLEL_SAFE_COMMANDS

    def test_write_commands_not_parallel_safe(self) -> None:
        assert "set-component-data" not in PARALLEL_SAFE_COMMANDS
        assert "run-tests" not in PARALLEL_SAFE_COMMANDS
        assert "compile" not in PARALLEL_SAFE_COMMANDS


# ---------------------------------------------------------------------------
# get_timeout
# ---------------------------------------------------------------------------


class TestGetTimeout:

    def test_command_override_wins(self) -> None:
        """command_override (per-command --timeout) has highest priority."""
        result = get_timeout("run-tests", command_override=999, global_override=50)
        assert result == 999

    def test_global_override_wins_over_default(self) -> None:
        result = get_timeout("run-tests", command_override=None, global_override=60)
        assert result == 60

    def test_falls_back_to_timeout_defaults(self) -> None:
        result = get_timeout("run-tests")
        assert result == TIMEOUT_DEFAULTS["run-tests"]
        assert result == 300

    def test_unknown_command_gets_30s_default(self) -> None:
        result = get_timeout("nonexistent-command")
        assert result == 30

    def test_command_override_none_falls_through(self) -> None:
        result = get_timeout("compile", command_override=None, global_override=None)
        assert result == 120

    def test_zero_override_is_valid(self) -> None:
        """A zero timeout override should be respected (not treated as None)."""
        result = get_timeout("run-tests", command_override=0)
        assert result == 0

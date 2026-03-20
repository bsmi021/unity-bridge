"""Unit tests for test listing operations in commands/testing.py — adversarial QA."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from unity_bridge.commands.testing import VALID_LIST_MODES, list_tests


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_parameters(call_args: Any) -> dict:
    if call_args.kwargs.get("parameters") is not None:
        return call_args.kwargs["parameters"]
    if len(call_args.args) >= 2:
        return call_args.args[1]
    return {}


def _extract_command_type(call_args: Any) -> str:
    if "command_type" in call_args.kwargs:
        return call_args.kwargs["command_type"]
    return call_args.args[0]


def _extract_kwarg(call_args: Any, key: str) -> Any:
    if key in call_args.kwargs:
        return call_args.kwargs[key]
    return None


# ---------------------------------------------------------------------------
# list tests (mode=tests)
# ---------------------------------------------------------------------------


class TestListTests:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await list_tests(mock_bridge)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "list-tests"

    async def test_default_mode_is_tests(self, mock_bridge: MagicMock) -> None:
        await list_tests(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["mode"] == "tests"

    async def test_custom_timeout(self, mock_bridge: MagicMock) -> None:
        await list_tests(mock_bridge, timeout=60.0)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 60.0

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        await list_tests(mock_bridge)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 30.0

    async def test_platform_editmode(self, mock_bridge: MagicMock) -> None:
        await list_tests(mock_bridge, platform="EditMode")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["testPlatform"] == "EditMode"

    async def test_platform_playmode(self, mock_bridge: MagicMock) -> None:
        await list_tests(mock_bridge, platform="PlayMode")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["testPlatform"] == "PlayMode"

    async def test_platform_omitted_by_default(self, mock_bridge: MagicMock) -> None:
        await list_tests(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "testPlatform" not in params

    async def test_filter_included(self, mock_bridge: MagicMock) -> None:
        await list_tests(mock_bridge, filter_pattern="Combat*")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["filter"] == "Combat*"

    async def test_filter_omitted_by_default(self, mock_bridge: MagicMock) -> None:
        await list_tests(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "filter" not in params

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await list_tests(failing_bridge)
        assert result.success is False


# ---------------------------------------------------------------------------
# list categories
# ---------------------------------------------------------------------------


class TestListCategories:
    async def test_sends_categories_mode(self, mock_bridge: MagicMock) -> None:
        await list_tests(mock_bridge, mode="categories")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["mode"] == "categories"

    async def test_with_platform(self, mock_bridge: MagicMock) -> None:
        await list_tests(mock_bridge, mode="categories", platform="PlayMode")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["mode"] == "categories"
        assert params["testPlatform"] == "PlayMode"


# ---------------------------------------------------------------------------
# list assemblies
# ---------------------------------------------------------------------------


class TestListAssemblies:
    async def test_sends_assemblies_mode(self, mock_bridge: MagicMock) -> None:
        await list_tests(mock_bridge, mode="assemblies")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["mode"] == "assemblies"

    async def test_with_platform(self, mock_bridge: MagicMock) -> None:
        await list_tests(mock_bridge, mode="assemblies", platform="EditMode")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["mode"] == "assemblies"
        assert params["testPlatform"] == "EditMode"


# ---------------------------------------------------------------------------
# VALID_LIST_MODES
# ---------------------------------------------------------------------------


class TestValidListModes:
    def test_all_three_modes_present(self) -> None:
        expected = {"tests", "categories", "assemblies"}
        assert VALID_LIST_MODES == expected

    def test_is_frozenset(self) -> None:
        assert isinstance(VALID_LIST_MODES, frozenset)


# ---------------------------------------------------------------------------
# Adversarial edge cases
# ---------------------------------------------------------------------------


class TestTestListAdversarial:
    async def test_invalid_mode_raises(self, mock_bridge: MagicMock) -> None:
        with pytest.raises(ValueError, match="Invalid list mode"):
            await list_tests(mock_bridge, mode="invalid")

    async def test_mode_case_insensitive(self, mock_bridge: MagicMock) -> None:
        """Mode should be lowercased before sending."""
        await list_tests(mock_bridge, mode="TESTS")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["mode"] == "tests"

    async def test_mode_whitespace_stripped(self, mock_bridge: MagicMock) -> None:
        await list_tests(mock_bridge, mode="  categories  ")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["mode"] == "categories"

    async def test_uses_send_command_with_retry(self, mock_bridge: MagicMock) -> None:
        await list_tests(mock_bridge)
        assert mock_bridge.send_command_with_retry.call_count == 1
        assert mock_bridge.send_command.call_count == 0

    async def test_filter_with_special_chars(self, mock_bridge: MagicMock) -> None:
        """Glob-like filter patterns should pass through."""
        await list_tests(mock_bridge, filter_pattern="*Integration*")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["filter"] == "*Integration*"

    async def test_empty_filter_still_sent(self, mock_bridge: MagicMock) -> None:
        """Empty string is different from None — should be sent."""
        await list_tests(mock_bridge, filter_pattern="")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["filter"] == ""

    async def test_list_tests_in_parallel_safe(self) -> None:
        """list-tests is read-only, should be in PARALLEL_SAFE_COMMANDS."""
        from unity_bridge.core.protocol import PARALLEL_SAFE_COMMANDS

        assert "list-tests" in PARALLEL_SAFE_COMMANDS

    async def test_in_timeout_defaults(self) -> None:
        """list-tests should be in TIMEOUT_DEFAULTS."""
        from unity_bridge.core.protocol import TIMEOUT_DEFAULTS

        assert "list-tests" in TIMEOUT_DEFAULTS

    async def test_all_modes_target_list_tests(self, mock_bridge: MagicMock) -> None:
        for mode in ("tests", "categories", "assemblies"):
            await list_tests(mock_bridge, mode=mode)
            cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
            assert cmd == "list-tests"

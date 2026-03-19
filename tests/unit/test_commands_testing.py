"""Unit tests for commands/testing.py — run_tests, compile_scripts."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from unity_bridge.commands.testing import compile_scripts, run_tests
from unity_bridge.core.bridge import CommandResult


# ---------------------------------------------------------------------------
# run_tests
# ---------------------------------------------------------------------------


class TestRunTests:

    async def test_passes_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await run_tests(mock_bridge)
        mock_bridge.send_command_with_retry.assert_awaited_once()
        call_kwargs = mock_bridge.send_command_with_retry.call_args
        assert call_kwargs.kwargs.get("command_type") == "run-tests" or \
            call_kwargs[1].get("command_type") == "run-tests" or \
            (call_kwargs[0] and call_kwargs[0][0] == "run-tests")

    async def test_default_platform_is_editmode(self, mock_bridge: MagicMock) -> None:
        await run_tests(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        # Parameters should include testPlatform=EditMode
        params = _extract_parameters(call_args)
        assert params["testPlatform"] == "EditMode"

    async def test_custom_platform(self, mock_bridge: MagicMock) -> None:
        await run_tests(mock_bridge, platform="PlayMode")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["testPlatform"] == "PlayMode"

    async def test_filter_pattern_included_when_provided(
        self, mock_bridge: MagicMock
    ) -> None:
        await run_tests(mock_bridge, filter_pattern="CombatTests")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["testFilter"] == "CombatTests"

    async def test_filter_pattern_omitted_when_none(
        self, mock_bridge: MagicMock
    ) -> None:
        await run_tests(mock_bridge, filter_pattern=None)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "testFilter" not in params

    async def test_timeout_passed_through(self, mock_bridge: MagicMock) -> None:
        await run_tests(mock_bridge, timeout=600)
        call_args = mock_bridge.send_command_with_retry.call_args
        timeout = _extract_kwarg(call_args, "timeout")
        assert timeout == 600.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        expected = CommandResult(success=True, data={"passed": 5})
        mock_bridge.send_command_with_retry.return_value = expected
        result = await run_tests(mock_bridge)
        assert result.success is True
        assert result.data["passed"] == 5


# ---------------------------------------------------------------------------
# compile_scripts
# ---------------------------------------------------------------------------


class TestCompileScripts:

    async def test_passes_compile_command(self, mock_bridge: MagicMock) -> None:
        await compile_scripts(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        cmd_type = _extract_command_type(call_args)
        assert cmd_type == "compile"

    async def test_wait_parameter_default_true(self, mock_bridge: MagicMock) -> None:
        await compile_scripts(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["waitForCompletion"] is True

    async def test_wait_parameter_false(self, mock_bridge: MagicMock) -> None:
        await compile_scripts(mock_bridge, wait=False)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["waitForCompletion"] is False

    async def test_timeout_passed(self, mock_bridge: MagicMock) -> None:
        await compile_scripts(mock_bridge, timeout=240)
        call_args = mock_bridge.send_command_with_retry.call_args
        timeout = _extract_kwarg(call_args, "timeout")
        assert timeout == 240.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_parameters(call_args: Any) -> dict:
    """Extract the 'parameters' kwarg from a mock call."""
    if call_args.kwargs.get("parameters") is not None:
        return call_args.kwargs["parameters"]
    # Positional: send_command_with_retry(command_type, parameters, ...)
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

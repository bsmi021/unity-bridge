"""Unit tests for commands/window.py — window management."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.core.bridge import CommandResult


def _import_window():
    from unity_bridge.commands import window

    return window


class TestWindowList:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_window()
        await mod.window_list(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "window-management"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_window()
        await mod.window_list(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "list"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_window()
        await mod.window_list(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 5.0


class TestWindowOpen:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_window()
        await mod.window_open(mock_bridge, "Inspector")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "open"
        assert params["windowName"] == "Inspector"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_window()
        await mod.window_open(mock_bridge, "Scene")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 10.0


class TestWindowFocus:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_window()
        await mod.window_focus(mock_bridge, "Scene")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "focus"
        assert params["windowName"] == "Scene"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_window()
        await mod.window_focus(mock_bridge, "Scene")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 5.0


class TestWindowClose:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_window()
        await mod.window_close(mock_bridge, "Console")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "close"
        assert params["windowName"] == "Console"

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_window()
        expected = CommandResult(success=True, data={"closedCount": 1})
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.window_close(mock_bridge, "Console")
        assert result.success is True
        assert result.data["closedCount"] == 1


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

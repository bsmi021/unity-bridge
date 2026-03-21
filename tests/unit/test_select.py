"""Unit tests for commands/select.py — set/clear editor selection."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.core.bridge import CommandResult


def _import_select():
    from unity_bridge.commands import select

    return select


# ---------------------------------------------------------------------------
# set_selection
# ---------------------------------------------------------------------------


class TestSetSelection:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_select()
        await mod.set_selection(mock_bridge, ["Player", "Main Camera"])
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "set-selection"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_select()
        await mod.set_selection(mock_bridge, ["Player", "Main Camera"])
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "set"
        assert params["gameObjectPaths"] == ["Player", "Main Camera"]

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_select()
        await mod.set_selection(mock_bridge, ["Player"])
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 5.0

    async def test_custom_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_select()
        await mod.set_selection(mock_bridge, ["Player"], timeout=10.0)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 10.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_select()
        expected = CommandResult(
            success=True,
            data={"selectedCount": 2, "selectedPaths": ["Player", "Main Camera"]},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.set_selection(mock_bridge, ["Player", "Main Camera"])
        assert result.success is True
        assert result.data["selectedCount"] == 2


# ---------------------------------------------------------------------------
# clear_selection
# ---------------------------------------------------------------------------


class TestClearSelection:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_select()
        await mod.clear_selection(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "set-selection"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_select()
        await mod.clear_selection(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "clear"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_select()
        await mod.clear_selection(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 5.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_select()
        expected = CommandResult(
            success=True,
            data={"selectedCount": 0, "operation": "clear"},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.clear_selection(mock_bridge)
        assert result.success is True
        assert result.data["selectedCount"] == 0


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

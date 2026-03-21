"""Unit tests for commands/clipboard.py — clipboard read/write."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.core.bridge import CommandResult


def _import_clipboard():
    from unity_bridge.commands import clipboard

    return clipboard


class TestClipboardRead:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_clipboard()
        await mod.clipboard_read(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "clipboard"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_clipboard()
        await mod.clipboard_read(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "read"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_clipboard()
        await mod.clipboard_read(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 5.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_clipboard()
        expected = CommandResult(success=True, data={"text": "hello", "length": 5})
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.clipboard_read(mock_bridge)
        assert result.success is True
        assert result.data["text"] == "hello"


class TestClipboardWrite:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_clipboard()
        await mod.clipboard_write(mock_bridge, "test text")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "clipboard"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_clipboard()
        await mod.clipboard_write(mock_bridge, "test text")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "write"
        assert params["text"] == "test text"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_clipboard()
        await mod.clipboard_write(mock_bridge, "test")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 5.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_clipboard()
        expected = CommandResult(success=True, data={"text": "test", "length": 4})
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.clipboard_write(mock_bridge, "test")
        assert result.success is True


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

"""Unit tests for commands/deep_serialize.py — EditorJsonUtility deep serialization."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.core.bridge import CommandResult


def _import_deep():
    from unity_bridge.commands import deep_serialize

    return deep_serialize


class TestDeepGet:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_deep()
        await mod.deep_get(mock_bridge, "Player", "Transform")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "deep-serialize"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_deep()
        await mod.deep_get(mock_bridge, "Player", "Transform")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "get"
        assert params["gameObjectPath"] == "Player"
        assert params["componentType"] == "Transform"
        assert params["prettyPrint"] is True

    async def test_compact_mode(self, mock_bridge: MagicMock) -> None:
        mod = _import_deep()
        await mod.deep_get(mock_bridge, "Player", "Transform", pretty_print=False)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["prettyPrint"] is False

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_deep()
        await mod.deep_get(mock_bridge, "Player", "Transform")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 10.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_deep()
        expected = CommandResult(success=True, data={"json": "{}", "operation": "get"})
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.deep_get(mock_bridge, "Player", "Transform")
        assert result.success is True


class TestDeepSet:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_deep()
        await mod.deep_set(mock_bridge, "Player", "Transform", '{"m_LocalPosition":{}}')
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "set"
        assert params["gameObjectPath"] == "Player"
        assert params["componentType"] == "Transform"
        assert params["json"] == '{"m_LocalPosition":{}}'

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_deep()
        await mod.deep_set(mock_bridge, "P", "T", "{}")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 15.0


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

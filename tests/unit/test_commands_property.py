"""Unit tests for commands/property.py — serialized property operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.commands.property import (
    property_get,
    property_list,
    property_set,
)


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
# property list
# ---------------------------------------------------------------------------


class TestPropertyList:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await property_list(mock_bridge, "Player", "Transform")
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "serialized-property"

    async def test_sends_list_operation(self, mock_bridge: MagicMock) -> None:
        await property_list(mock_bridge, "Player", "Transform")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "list"
        assert params["gameObjectPath"] == "Player"
        assert params["componentType"] == "Transform"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        await property_list(mock_bridge, "Player", "Transform")
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 10.0

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await property_list(failing_bridge, "Player", "Transform")
        assert result.success is False


# ---------------------------------------------------------------------------
# property get
# ---------------------------------------------------------------------------


class TestPropertyGet:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await property_get(mock_bridge, "Player", "Transform", "m_LocalPosition")
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "serialized-property"

    async def test_sends_get_operation(self, mock_bridge: MagicMock) -> None:
        await property_get(mock_bridge, "Player", "MyScript", "health")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "get"
        assert params["propertyPath"] == "health"

    async def test_nested_path(self, mock_bridge: MagicMock) -> None:
        await property_get(mock_bridge, "Player", "MyScript", "stats.maxHp")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["propertyPath"] == "stats.maxHp"

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await property_get(failing_bridge, "P", "T", "x")
        assert result.success is False


# ---------------------------------------------------------------------------
# property set
# ---------------------------------------------------------------------------


class TestPropertySet:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await property_set(mock_bridge, "Player", "MyScript", "health", "100")
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "serialized-property"

    async def test_sends_set_operation(self, mock_bridge: MagicMock) -> None:
        await property_set(mock_bridge, "Player", "MyScript", "health", "100")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "set"
        assert params["propertyPath"] == "health"
        assert params["valueJson"] == "100"

    async def test_json_object_value(self, mock_bridge: MagicMock) -> None:
        await property_set(
            mock_bridge, "Player", "Transform", "m_LocalPosition", '{"x":1,"y":2,"z":3}'
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["valueJson"] == '{"x":1,"y":2,"z":3}'

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        await property_set(mock_bridge, "P", "T", "x", "1")
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 30.0

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await property_set(failing_bridge, "P", "T", "x", "1")
        assert result.success is False


# ---------------------------------------------------------------------------
# Adversarial
# ---------------------------------------------------------------------------


class TestPropertyAdversarial:
    async def test_all_operations_use_send_command_with_retry(self, mock_bridge: MagicMock) -> None:
        await property_list(mock_bridge, "P", "T")
        await property_get(mock_bridge, "P", "T", "x")
        await property_set(mock_bridge, "P", "T", "x", "1")
        assert mock_bridge.send_command_with_retry.call_count == 3
        assert mock_bridge.send_command.call_count == 0

    async def test_special_chars_in_property_path(self, mock_bridge: MagicMock) -> None:
        await property_get(mock_bridge, "P", "T", "m_Array.Array.data[0]")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["propertyPath"] == "m_Array.Array.data[0]"

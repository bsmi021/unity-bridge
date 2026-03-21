"""Unit tests for commands/transform.py — all 4 transform operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.commands.transform import (
    transform_get,
    transform_parent,
    transform_set,
    transform_sibling_index,
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
# transform get
# ---------------------------------------------------------------------------


class TestTransformGet:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await transform_get(mock_bridge, "Player")
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "transform-operation"

    async def test_sends_get_operation(self, mock_bridge: MagicMock) -> None:
        await transform_get(mock_bridge, "Player")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "get"
        assert params["gameObjectPath"] == "Player"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        await transform_get(mock_bridge, "Player")
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 10.0

    async def test_custom_timeout(self, mock_bridge: MagicMock) -> None:
        await transform_get(mock_bridge, "Player", timeout=20.0)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 20.0

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await transform_get(failing_bridge, "Player")
        assert result.success is False


# ---------------------------------------------------------------------------
# transform set
# ---------------------------------------------------------------------------


class TestTransformSet:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await transform_set(mock_bridge, "Player", position=(1, 2, 3))
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "transform-operation"

    async def test_sends_position(self, mock_bridge: MagicMock) -> None:
        await transform_set(mock_bridge, "Player", position=(1, 2, 3))
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "set"
        assert params["position"]["x"] == 1
        assert params["position"]["y"] == 2
        assert params["position"]["z"] == 3
        assert params["position"]["isSet"] is True

    async def test_sends_rotation(self, mock_bridge: MagicMock) -> None:
        await transform_set(mock_bridge, "Player", rotation=(45, 90, 0))
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["rotation"]["x"] == 45

    async def test_sends_scale(self, mock_bridge: MagicMock) -> None:
        await transform_set(mock_bridge, "Player", scale=(2, 2, 2))
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["scale"]["x"] == 2

    async def test_local_flag(self, mock_bridge: MagicMock) -> None:
        await transform_set(mock_bridge, "Player", position=(0, 0, 0), local=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["useLocal"] is True
        assert "localPosition" in params

    async def test_no_position_when_not_specified(self, mock_bridge: MagicMock) -> None:
        await transform_set(mock_bridge, "Player", rotation=(0, 90, 0))
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "position" not in params

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await transform_set(failing_bridge, "Player", position=(0, 0, 0))
        assert result.success is False


# ---------------------------------------------------------------------------
# transform parent
# ---------------------------------------------------------------------------


class TestTransformParent:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await transform_parent(mock_bridge, "Player", "World")
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "transform-operation"

    async def test_sends_parent_operation(self, mock_bridge: MagicMock) -> None:
        await transform_parent(mock_bridge, "Player", "World")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "parent"
        assert params["parentPath"] == "World"

    async def test_world_position_stays_default(self, mock_bridge: MagicMock) -> None:
        await transform_parent(mock_bridge, "Player", "World")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["worldPositionStays"] is True

    async def test_world_position_stays_false(self, mock_bridge: MagicMock) -> None:
        await transform_parent(mock_bridge, "Player", "World", world_position_stays=False)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["worldPositionStays"] is False

    async def test_unparent(self, mock_bridge: MagicMock) -> None:
        await transform_parent(mock_bridge, "Player")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "parentPath" not in params

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await transform_parent(failing_bridge, "Player", "World")
        assert result.success is False


# ---------------------------------------------------------------------------
# transform sibling-index
# ---------------------------------------------------------------------------


class TestTransformSiblingIndex:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await transform_sibling_index(mock_bridge, "Player", 0)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "transform-operation"

    async def test_sends_sibling_index_operation(self, mock_bridge: MagicMock) -> None:
        await transform_sibling_index(mock_bridge, "Player", 3)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "sibling-index"
        assert params["siblingIndex"] == 3

    async def test_zero_index(self, mock_bridge: MagicMock) -> None:
        await transform_sibling_index(mock_bridge, "Player", 0)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["siblingIndex"] == 0

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await transform_sibling_index(failing_bridge, "Player", 0)
        assert result.success is False


# ---------------------------------------------------------------------------
# Adversarial / edge cases
# ---------------------------------------------------------------------------


class TestTransformAdversarial:
    async def test_all_operations_use_send_command_with_retry(self, mock_bridge: MagicMock) -> None:
        await transform_get(mock_bridge, "P")
        await transform_set(mock_bridge, "P", position=(0, 0, 0))
        await transform_parent(mock_bridge, "P", "W")
        await transform_sibling_index(mock_bridge, "P", 0)
        assert mock_bridge.send_command_with_retry.call_count == 4
        assert mock_bridge.send_command.call_count == 0

    async def test_path_with_slashes(self, mock_bridge: MagicMock) -> None:
        await transform_get(mock_bridge, "Root/Child/Grandchild")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["gameObjectPath"] == "Root/Child/Grandchild"

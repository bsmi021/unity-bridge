"""Unit tests for commands/physics_config.py — physics configuration operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.commands.physics_config import (
    physics_collision_get,
    physics_collision_set,
    physics_get,
    physics_set,
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
# physics get
# ---------------------------------------------------------------------------


class TestPhysicsGet:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await physics_get(mock_bridge)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "physics-config"

    async def test_sends_get_operation(self, mock_bridge: MagicMock) -> None:
        await physics_get(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "get"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        await physics_get(mock_bridge)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 10.0

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await physics_get(failing_bridge)
        assert result.success is False


# ---------------------------------------------------------------------------
# physics set
# ---------------------------------------------------------------------------


class TestPhysicsSet:
    async def test_sends_gravity(self, mock_bridge: MagicMock) -> None:
        await physics_set(mock_bridge, gravity=(0, -9.81, 0))
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "set"
        assert params["gravity"]["y"] == -9.81
        assert params["gravity"]["isSet"] is True

    async def test_sends_solver_iterations(self, mock_bridge: MagicMock) -> None:
        await physics_set(mock_bridge, solver_iterations=12)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["defaultSolverIterations"] == 12

    async def test_no_gravity_when_not_specified(self, mock_bridge: MagicMock) -> None:
        await physics_set(mock_bridge, solver_iterations=6)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "gravity" not in params

    async def test_auto_sync_transforms(self, mock_bridge: MagicMock) -> None:
        await physics_set(mock_bridge, auto_sync_transforms=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["autoSyncTransforms"] is True
        assert params["setAutoSyncTransforms"] is True

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await physics_set(failing_bridge, gravity=(0, -10, 0))
        assert result.success is False


# ---------------------------------------------------------------------------
# collision matrix
# ---------------------------------------------------------------------------


class TestPhysicsCollisionGet:
    async def test_sends_correct_operation(self, mock_bridge: MagicMock) -> None:
        await physics_collision_get(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "collision-matrix-get"

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await physics_collision_get(failing_bridge)
        assert result.success is False


class TestPhysicsCollisionSet:
    async def test_sends_correct_operation(self, mock_bridge: MagicMock) -> None:
        await physics_collision_set(mock_bridge, 0, 8, ignore=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "collision-matrix-set"
        assert params["layer1"] == 0
        assert params["layer2"] == 8
        assert params["ignoreCollision"] is True

    async def test_ignore_default_false(self, mock_bridge: MagicMock) -> None:
        await physics_collision_set(mock_bridge, 1, 2)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["ignoreCollision"] is False

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await physics_collision_set(failing_bridge, 0, 1)
        assert result.success is False


# ---------------------------------------------------------------------------
# Adversarial
# ---------------------------------------------------------------------------


class TestPhysicsAdversarial:
    async def test_all_operations_use_send_command_with_retry(self, mock_bridge: MagicMock) -> None:
        await physics_get(mock_bridge)
        await physics_set(mock_bridge, gravity=(0, -10, 0))
        await physics_collision_get(mock_bridge)
        await physics_collision_set(mock_bridge, 0, 1)
        assert mock_bridge.send_command_with_retry.call_count == 4
        assert mock_bridge.send_command.call_count == 0

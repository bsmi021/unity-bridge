"""Unit tests for commands/navmesh.py — NavMesh operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock


from unity_bridge.core.bridge import CommandResult


def _import_navmesh():
    from unity_bridge.commands import navmesh

    return navmesh


# ---------------------------------------------------------------------------
# bake
# ---------------------------------------------------------------------------


class TestBake:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_navmesh()
        await mod.navmesh_bake(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "navmesh-operation"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_navmesh()
        await mod.navmesh_bake(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "bake"}

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_navmesh()
        await mod.navmesh_bake(mock_bridge)
        assert _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout") == 60.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_navmesh()
        expected = CommandResult(
            success=True,
            data={"operation": "bake", "success": True, "message": "NavMesh baked"},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.navmesh_bake(mock_bridge)
        assert result.success is True


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------


class TestClear:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_navmesh()
        await mod.navmesh_clear(mock_bridge)
        assert (
            _extract_command_type(mock_bridge.send_command_with_retry.call_args)
            == "navmesh-operation"
        )

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_navmesh()
        await mod.navmesh_clear(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "clear"}


# ---------------------------------------------------------------------------
# get-settings
# ---------------------------------------------------------------------------


class TestGetSettings:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_navmesh()
        await mod.navmesh_get_settings(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "get-settings"}

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_navmesh()
        await mod.navmesh_get_settings(mock_bridge)
        assert _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout") == 10.0


# ---------------------------------------------------------------------------
# set-settings
# ---------------------------------------------------------------------------


class TestSetSettings:
    async def test_sends_agent_radius(self, mock_bridge: MagicMock) -> None:
        mod = _import_navmesh()
        await mod.navmesh_set_settings(mock_bridge, agent_radius=0.5)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "set-settings"
        assert params["agentRadius"] == 0.5

    async def test_sends_all_settings(self, mock_bridge: MagicMock) -> None:
        mod = _import_navmesh()
        await mod.navmesh_set_settings(
            mock_bridge, agent_radius=0.4, agent_height=2.0, max_slope=45.0, step_height=0.4
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["agentRadius"] == 0.4
        assert params["agentHeight"] == 2.0
        assert params["agentSlope"] == 45.0
        assert params["agentClimb"] == 0.4


# ---------------------------------------------------------------------------
# get-areas
# ---------------------------------------------------------------------------


class TestGetAreas:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_navmesh()
        await mod.navmesh_get_areas(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "get-areas"}

    async def test_returns_area_data(self, mock_bridge: MagicMock) -> None:
        mod = _import_navmesh()
        expected = CommandResult(
            success=True,
            data={
                "operation": "get-areas",
                "areas": [
                    {"name": "Walkable", "index": 0, "cost": 1.0},
                    {"name": "Not Walkable", "index": 1, "cost": 1.0},
                ],
                "success": True,
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.navmesh_get_areas(mock_bridge)
        assert len(result.data["areas"]) == 2


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

"""Unit tests for commands/terrain.py — Terrain operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock


from unity_bridge.core.bridge import CommandResult


def _import_terrain():
    from unity_bridge.commands import terrain

    return terrain


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestCreate:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_terrain()
        await mod.terrain_create(mock_bridge, name="MyTerrain")
        assert (
            _extract_command_type(mock_bridge.send_command_with_retry.call_args)
            == "terrain-operation"
        )

    async def test_sends_name_and_size(self, mock_bridge: MagicMock) -> None:
        mod = _import_terrain()
        await mod.terrain_create(mock_bridge, name="TestTerrain", size=(500, 300, 500))
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "create"
        assert params["terrainName"] == "TestTerrain"
        assert params["sizeX"] == 500
        assert params["sizeY"] == 300
        assert params["sizeZ"] == 500

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_terrain()
        await mod.terrain_create(mock_bridge)
        assert _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout") == 30.0


# ---------------------------------------------------------------------------
# get-info
# ---------------------------------------------------------------------------


class TestGetInfo:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_terrain()
        await mod.terrain_get_info(mock_bridge, "MyTerrain")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "get-info", "terrainName": "MyTerrain"}

    async def test_returns_terrain_info(self, mock_bridge: MagicMock) -> None:
        mod = _import_terrain()
        expected = CommandResult(
            success=True,
            data={
                "operation": "get-info",
                "terrainName": "Terrain",
                "heightmapResolution": 513,
                "sizeX": 1000,
                "sizeY": 600,
                "sizeZ": 1000,
                "alphamapLayers": 4,
                "treeInstanceCount": 50,
                "success": True,
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.terrain_get_info(mock_bridge)
        assert result.data["heightmapResolution"] == 513
        assert result.data["alphamapLayers"] == 4


# ---------------------------------------------------------------------------
# get-heights
# ---------------------------------------------------------------------------


class TestGetHeights:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_terrain()
        await mod.terrain_get_heights(mock_bridge, x=10, y=20, width=8, height=8)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "get-heights"
        assert params["heightX"] == 10
        assert params["heightY"] == 20
        assert params["heightWidth"] == 8
        assert params["heightHeight"] == 8


# ---------------------------------------------------------------------------
# set-heights
# ---------------------------------------------------------------------------


class TestSetHeights:
    async def test_sends_height_data(self, mock_bridge: MagicMock) -> None:
        mod = _import_terrain()
        heights = [[0.1, 0.2], [0.3, 0.4]]
        await mod.terrain_set_heights(mock_bridge, x=0, y=0, heights=heights)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "set-heights"
        assert len(params["heights"]) == 2
        assert params["heights"][0]["values"] == [0.1, 0.2]


# ---------------------------------------------------------------------------
# set-settings
# ---------------------------------------------------------------------------


class TestSetSettings:
    async def test_sends_size(self, mock_bridge: MagicMock) -> None:
        mod = _import_terrain()
        await mod.terrain_set_settings(mock_bridge, size=(2000, 800, 2000))
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "set-settings"
        assert params["sizeX"] == 2000
        assert params["sizeY"] == 800

    async def test_sends_resolution(self, mock_bridge: MagicMock) -> None:
        mod = _import_terrain()
        await mod.terrain_set_settings(mock_bridge, heightmap_resolution=1025)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["heightmapResolution"] == 1025


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

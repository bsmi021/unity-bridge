"""Unit tests for commands/tilemap.py — Tilemap operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock


from unity_bridge.core.bridge import CommandResult


def _import_tilemap():
    from unity_bridge.commands import tilemap

    return tilemap


# ---------------------------------------------------------------------------
# set-tile
# ---------------------------------------------------------------------------


class TestSetTile:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_tilemap()
        await mod.tilemap_set_tile(mock_bridge, "Grid/Tilemap", 1, 2, 0, "Assets/Tiles/Grass.asset")
        assert (
            _extract_command_type(mock_bridge.send_command_with_retry.call_args)
            == "tilemap-operation"
        )

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_tilemap()
        await mod.tilemap_set_tile(mock_bridge, "Grid/Tilemap", 3, 4, 0, "Assets/Tiles/Grass.asset")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "set-tile"
        assert params["tilemapPath"] == "Grid/Tilemap"
        assert params["posX"] == 3
        assert params["posY"] == 4
        assert params["tilePath"] == "Assets/Tiles/Grass.asset"


# ---------------------------------------------------------------------------
# get-tile
# ---------------------------------------------------------------------------


class TestGetTile:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_tilemap()
        await mod.tilemap_get_tile(mock_bridge, "Grid/Tilemap", 1, 2)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "get-tile"
        assert params["posX"] == 1
        assert params["posY"] == 2

    async def test_returns_tile_data(self, mock_bridge: MagicMock) -> None:
        mod = _import_tilemap()
        expected = CommandResult(
            success=True,
            data={
                "operation": "get-tile",
                "hasTile": True,
                "tileName": "Grass",
                "success": True,
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.tilemap_get_tile(mock_bridge, "Grid/Tilemap", 1, 2)
        assert result.data["hasTile"] is True
        assert result.data["tileName"] == "Grass"


# ---------------------------------------------------------------------------
# fill-box
# ---------------------------------------------------------------------------


class TestFillBox:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_tilemap()
        await mod.tilemap_fill_box(
            mock_bridge, "Grid/Tilemap", "Assets/Tiles/Grass.asset", 0, 0, 5, 5
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "fill-box"
        assert params["startX"] == 0
        assert params["endX"] == 5


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------


class TestClear:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_tilemap()
        await mod.tilemap_clear(mock_bridge, "Grid/Tilemap")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "clear", "tilemapPath": "Grid/Tilemap"}


# ---------------------------------------------------------------------------
# get-bounds
# ---------------------------------------------------------------------------


class TestGetBounds:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_tilemap()
        await mod.tilemap_get_bounds(mock_bridge, "Grid/Tilemap")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "get-bounds", "tilemapPath": "Grid/Tilemap"}

    async def test_returns_bounds_data(self, mock_bridge: MagicMock) -> None:
        mod = _import_tilemap()
        expected = CommandResult(
            success=True,
            data={
                "operation": "get-bounds",
                "minX": -5,
                "minY": -3,
                "maxX": 10,
                "maxY": 8,
                "success": True,
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.tilemap_get_bounds(mock_bridge, "Grid/Tilemap")
        assert result.data["minX"] == -5
        assert result.data["maxX"] == 10


# ---------------------------------------------------------------------------
# compress-bounds
# ---------------------------------------------------------------------------


class TestCompressBounds:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_tilemap()
        await mod.tilemap_compress_bounds(mock_bridge, "Grid/Tilemap")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "compress-bounds", "tilemapPath": "Grid/Tilemap"}


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

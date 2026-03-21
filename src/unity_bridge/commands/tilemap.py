"""Tilemap commands: set-tile, get-tile, fill-box, clear, get-bounds, compress-bounds."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def tilemap_set_tile(
    bridge: DirectBridge,
    tilemap_path: str,
    x: int,
    y: int,
    z: int,
    tile_path: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Place a tile at position.

    Args:
        bridge: Active bridge connection.
        tilemap_path: Hierarchy path to the Tilemap.
        x: Cell X coordinate.
        y: Cell Y coordinate.
        z: Cell Z coordinate.
        tile_path: Asset path to the tile.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="tilemap-operation",
        parameters={
            "operation": "set-tile",
            "tilemapPath": tilemap_path,
            "posX": x,
            "posY": y,
            "posZ": z,
            "tilePath": tile_path,
        },
        timeout=timeout,
    )


async def tilemap_get_tile(
    bridge: DirectBridge,
    tilemap_path: str,
    x: int,
    y: int,
    z: int = 0,
    timeout: float = 10.0,
) -> CommandResult:
    """Get tile at position.

    Args:
        bridge: Active bridge connection.
        tilemap_path: Hierarchy path to the Tilemap.
        x: Cell X coordinate.
        y: Cell Y coordinate.
        z: Cell Z coordinate.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="tilemap-operation",
        parameters={
            "operation": "get-tile",
            "tilemapPath": tilemap_path,
            "posX": x,
            "posY": y,
            "posZ": z,
        },
        timeout=timeout,
    )


async def tilemap_fill_box(
    bridge: DirectBridge,
    tilemap_path: str,
    tile_path: str,
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    timeout: float = 15.0,
) -> CommandResult:
    """Fill a rectangular area with tiles.

    Args:
        bridge: Active bridge connection.
        tilemap_path: Hierarchy path to the Tilemap.
        tile_path: Asset path to the tile.
        start_x: Start X.
        start_y: Start Y.
        end_x: End X.
        end_y: End Y.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="tilemap-operation",
        parameters={
            "operation": "fill-box",
            "tilemapPath": tilemap_path,
            "tilePath": tile_path,
            "startX": start_x,
            "startY": start_y,
            "endX": end_x,
            "endY": end_y,
        },
        timeout=timeout,
    )


async def tilemap_clear(
    bridge: DirectBridge,
    tilemap_path: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Clear all tiles from a tilemap.

    Args:
        bridge: Active bridge connection.
        tilemap_path: Hierarchy path to the Tilemap.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="tilemap-operation",
        parameters={"operation": "clear", "tilemapPath": tilemap_path},
        timeout=timeout,
    )


async def tilemap_get_bounds(
    bridge: DirectBridge,
    tilemap_path: str,
    timeout: float = 10.0,
) -> CommandResult:
    """Get tilemap cell bounds.

    Args:
        bridge: Active bridge connection.
        tilemap_path: Hierarchy path to the Tilemap.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="tilemap-operation",
        parameters={"operation": "get-bounds", "tilemapPath": tilemap_path},
        timeout=timeout,
    )


async def tilemap_compress_bounds(
    bridge: DirectBridge,
    tilemap_path: str,
    timeout: float = 10.0,
) -> CommandResult:
    """Compress tilemap bounds to used area.

    Args:
        bridge: Active bridge connection.
        tilemap_path: Hierarchy path to the Tilemap.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="tilemap-operation",
        parameters={"operation": "compress-bounds", "tilemapPath": tilemap_path},
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

tilemap_app = typer.Typer(name="tilemap", help="2D Tilemap commands.")


@tilemap_app.command("set-tile")
def tilemap_set_tile_cli(
    ctx: typer.Context,
    tilemap_path: Annotated[str, typer.Argument(help="Hierarchy path to Tilemap.")],
    tile_path: Annotated[str, typer.Argument(help="Asset path to tile.")],
    x: Annotated[int, typer.Option(help="Cell X.")] = 0,
    y: Annotated[int, typer.Option(help="Cell Y.")] = 0,
    z: Annotated[int, typer.Option(help="Cell Z.")] = 0,
) -> None:
    """Place a tile at position."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(tilemap_set_tile(state.bridge, tilemap_path, x, y, z, tile_path))
    print_result(result, state.formatter)


@tilemap_app.command("get-tile")
def tilemap_get_tile_cli(
    ctx: typer.Context,
    tilemap_path: Annotated[str, typer.Argument(help="Hierarchy path to Tilemap.")],
    x: Annotated[int, typer.Option(help="Cell X.")] = 0,
    y: Annotated[int, typer.Option(help="Cell Y.")] = 0,
) -> None:
    """Get tile at position."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(tilemap_get_tile(state.bridge, tilemap_path, x, y))
    print_result(result, state.formatter)


@tilemap_app.command("clear")
def tilemap_clear_cli(
    ctx: typer.Context,
    tilemap_path: Annotated[str, typer.Argument(help="Hierarchy path to Tilemap.")],
) -> None:
    """Clear all tiles from a tilemap."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(tilemap_clear(state.bridge, tilemap_path))
    print_result(result, state.formatter)


@tilemap_app.command("bounds")
def tilemap_bounds_cli(
    ctx: typer.Context,
    tilemap_path: Annotated[str, typer.Argument(help="Hierarchy path to Tilemap.")],
) -> None:
    """Get tilemap cell bounds."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(tilemap_get_bounds(state.bridge, tilemap_path))
    print_result(result, state.formatter)

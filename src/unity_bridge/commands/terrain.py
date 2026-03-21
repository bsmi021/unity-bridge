"""Terrain commands: create, info, heights get/set, settings."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_size(value: str) -> tuple[float, float, float]:
    """Parse 'X,Y,Z' size string."""
    parts = value.split(",")
    if len(parts) != 3:
        raise typer.BadParameter(f"Expected X,Y,Z format, got '{value}'")
    try:
        return (float(parts[0]), float(parts[1]), float(parts[2]))
    except ValueError:
        raise typer.BadParameter(f"Non-numeric value in '{value}'")


# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def terrain_create(
    bridge: DirectBridge,
    name: str | None = None,
    size: tuple[float, float, float] | None = None,
    heightmap_resolution: int | None = None,
    terrain_data_path: str | None = None,
    timeout: float = 30.0,
) -> CommandResult:
    """Create a new Terrain with TerrainData.

    Args:
        bridge: Active bridge connection.
        name: Name for the terrain GameObject.
        size: Terrain size as (x, y, z).
        heightmap_resolution: Heightmap resolution.
        terrain_data_path: Asset path for TerrainData.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {"operation": "create"}
    if name is not None:
        params["terrainName"] = name
    if size is not None:
        params["sizeX"] = size[0]
        params["sizeY"] = size[1]
        params["sizeZ"] = size[2]
    if heightmap_resolution is not None:
        params["heightmapResolution"] = heightmap_resolution
    if terrain_data_path is not None:
        params["terrainDataPath"] = terrain_data_path

    return await bridge.send_command_with_retry(
        command_type="terrain-operation",
        parameters=params,
        timeout=timeout,
    )


async def terrain_get_info(
    bridge: DirectBridge,
    terrain_name: str | None = None,
    timeout: float = 10.0,
) -> CommandResult:
    """Get terrain info.

    Args:
        bridge: Active bridge connection.
        terrain_name: Name of the terrain GameObject.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {"operation": "get-info"}
    if terrain_name is not None:
        params["terrainName"] = terrain_name
    return await bridge.send_command_with_retry(
        command_type="terrain-operation",
        parameters=params,
        timeout=timeout,
    )


async def terrain_get_heights(
    bridge: DirectBridge,
    x: int = 0,
    y: int = 0,
    width: int = 16,
    height: int = 16,
    terrain_name: str | None = None,
    timeout: float = 10.0,
) -> CommandResult:
    """Read heightmap region.

    Args:
        bridge: Active bridge connection.
        x: Start X coordinate.
        y: Start Y coordinate.
        width: Width of region.
        height: Height of region.
        terrain_name: Name of the terrain.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {
        "operation": "get-heights",
        "heightX": x,
        "heightY": y,
        "heightWidth": width,
        "heightHeight": height,
    }
    if terrain_name is not None:
        params["terrainName"] = terrain_name
    return await bridge.send_command_with_retry(
        command_type="terrain-operation",
        parameters=params,
        timeout=timeout,
    )


async def terrain_set_heights(
    bridge: DirectBridge,
    x: int,
    y: int,
    heights: list[list[float]],
    terrain_name: str | None = None,
    timeout: float = 30.0,
) -> CommandResult:
    """Set heightmap region.

    Args:
        bridge: Active bridge connection.
        x: Start X coordinate.
        y: Start Y coordinate.
        heights: 2D array of height values (0-1 range).
        terrain_name: Name of the terrain.
        timeout: Timeout in seconds.
    """
    height_rows = [{"values": row} for row in heights]
    params: dict[str, object] = {
        "operation": "set-heights",
        "heightX": x,
        "heightY": y,
        "heights": height_rows,
    }
    if terrain_name is not None:
        params["terrainName"] = terrain_name
    return await bridge.send_command_with_retry(
        command_type="terrain-operation",
        parameters=params,
        timeout=timeout,
    )


async def terrain_set_settings(
    bridge: DirectBridge,
    size: tuple[float, float, float] | None = None,
    heightmap_resolution: int | None = None,
    terrain_name: str | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Set terrain settings.

    Args:
        bridge: Active bridge connection.
        size: Terrain size as (x, y, z).
        heightmap_resolution: Heightmap resolution.
        terrain_name: Name of the terrain.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {"operation": "set-settings"}
    if terrain_name is not None:
        params["terrainName"] = terrain_name
    if size is not None:
        params["sizeX"] = size[0]
        params["sizeY"] = size[1]
        params["sizeZ"] = size[2]
    if heightmap_resolution is not None:
        params["heightmapResolution"] = heightmap_resolution
    return await bridge.send_command_with_retry(
        command_type="terrain-operation",
        parameters=params,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

terrain_app = typer.Typer(name="terrain", help="Terrain commands.")


@terrain_app.command("create")
def terrain_create_cli(
    ctx: typer.Context,
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Terrain name."),
    ] = None,
    size: Annotated[
        str | None,
        typer.Option("--size", "-s", help="Terrain size as X,Y,Z."),
    ] = None,
) -> None:
    """Create a new Terrain."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    sz = _parse_size(size) if size else None
    result = asyncio.run(terrain_create(state.bridge, name=name, size=sz))
    print_result(result, state.formatter)


@terrain_app.command("info")
def terrain_info_cli(
    ctx: typer.Context,
    terrain_name: Annotated[
        str | None,
        typer.Argument(help="Terrain name (optional, uses active terrain)."),
    ] = None,
) -> None:
    """Get terrain info."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(terrain_get_info(state.bridge, terrain_name))
    print_result(result, state.formatter)


# -- Heights sub-group ---------------------------------------------------

heights_app = typer.Typer(name="heights", help="Terrain height operations.")
terrain_app.add_typer(heights_app, name="heights")


@heights_app.command("get")
def heights_get_cli(
    ctx: typer.Context,
    x: Annotated[int, typer.Option(help="Start X.")] = 0,
    y: Annotated[int, typer.Option(help="Start Y.")] = 0,
    width: Annotated[int, typer.Option("--width", "-w", help="Width.")] = 16,
    height: Annotated[int, typer.Option("--height", "-h", help="Height.")] = 16,
) -> None:
    """Get heightmap region."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(terrain_get_heights(state.bridge, x, y, width, height))
    print_result(result, state.formatter)

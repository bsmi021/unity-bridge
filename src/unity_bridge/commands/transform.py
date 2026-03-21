"""Transform manipulation commands: get, set, parent, sibling-index."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def transform_get(
    bridge: DirectBridge,
    object_path: str,
    timeout: float = 10.0,
) -> CommandResult:
    """Get all transform data for a GameObject.

    Args:
        bridge: Active bridge connection.
        object_path: Hierarchy path to the GameObject.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="transform-operation",
        parameters={"operation": "get", "gameObjectPath": object_path},
        timeout=timeout,
    )


async def transform_set(
    bridge: DirectBridge,
    object_path: str,
    position: tuple[float, float, float] | None = None,
    rotation: tuple[float, float, float] | None = None,
    scale: tuple[float, float, float] | None = None,
    local: bool = False,
    timeout: float = 30.0,
) -> CommandResult:
    """Set transform values on a GameObject.

    Args:
        bridge: Active bridge connection.
        object_path: Hierarchy path to the GameObject.
        position: World or local position (x, y, z).
        rotation: Euler rotation (x, y, z).
        scale: Local scale (x, y, z).
        local: Use localPosition instead of world position.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {
        "operation": "set",
        "gameObjectPath": object_path,
        "useLocal": local,
    }
    if position is not None:
        key = "localPosition" if local else "position"
        params[key] = {"x": position[0], "y": position[1], "z": position[2], "isSet": True}
    if rotation is not None:
        params["rotation"] = {"x": rotation[0], "y": rotation[1], "z": rotation[2], "isSet": True}
    if scale is not None:
        params["scale"] = {"x": scale[0], "y": scale[1], "z": scale[2], "isSet": True}

    return await bridge.send_command_with_retry(
        command_type="transform-operation",
        parameters=params,
        timeout=timeout,
    )


async def transform_parent(
    bridge: DirectBridge,
    object_path: str,
    new_parent: str | None = None,
    world_position_stays: bool = True,
    timeout: float = 30.0,
) -> CommandResult:
    """Reparent a GameObject.

    Args:
        bridge: Active bridge connection.
        object_path: Hierarchy path to the GameObject.
        new_parent: Hierarchy path of the new parent (None to unparent).
        world_position_stays: Preserve world position during reparent.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {
        "operation": "parent",
        "gameObjectPath": object_path,
        "worldPositionStays": world_position_stays,
    }
    if new_parent is not None:
        params["parentPath"] = new_parent

    return await bridge.send_command_with_retry(
        command_type="transform-operation",
        parameters=params,
        timeout=timeout,
    )


async def transform_sibling_index(
    bridge: DirectBridge,
    object_path: str,
    index: int,
    timeout: float = 30.0,
) -> CommandResult:
    """Set sibling index (hierarchy order within parent).

    Args:
        bridge: Active bridge connection.
        object_path: Hierarchy path to the GameObject.
        index: Target sibling index.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="transform-operation",
        parameters={
            "operation": "sibling-index",
            "gameObjectPath": object_path,
            "siblingIndex": index,
        },
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_vector3(value: str) -> tuple[float, float, float]:
    """Parse 'X,Y,Z' string into a 3-tuple of floats."""
    parts = value.split(",")
    if len(parts) != 3:
        raise typer.BadParameter(f"Expected X,Y,Z format, got '{value}'")
    try:
        return (float(parts[0]), float(parts[1]), float(parts[2]))
    except ValueError:
        raise typer.BadParameter(f"Non-numeric value in '{value}'")


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

transform_app = typer.Typer(name="transform", help="Transform manipulation commands.")


@transform_app.command("get")
def transform_get_cli(
    ctx: typer.Context,
    object_path: Annotated[str, typer.Argument(help="Hierarchy path to the GameObject.")],
) -> None:
    """Get all transform data for a GameObject."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(transform_get(state.bridge, object_path))
    print_result(result, state.formatter)


@transform_app.command("set")
def transform_set_cli(
    ctx: typer.Context,
    object_path: Annotated[str, typer.Argument(help="Hierarchy path to the GameObject.")],
    position: Annotated[
        str | None,
        typer.Option("--position", "-p", help="Position as X,Y,Z."),
    ] = None,
    rotation: Annotated[
        str | None,
        typer.Option("--rotation", "-r", help="Euler rotation as X,Y,Z."),
    ] = None,
    scale: Annotated[
        str | None,
        typer.Option("--scale", "-s", help="Local scale as X,Y,Z."),
    ] = None,
    local: Annotated[
        bool,
        typer.Option("--local", help="Use local position instead of world."),
    ] = False,
) -> None:
    """Set transform position, rotation, and/or scale."""
    from unity_bridge.core.output import print_result

    pos = _parse_vector3(position) if position else None
    rot = _parse_vector3(rotation) if rotation else None
    scl = _parse_vector3(scale) if scale else None

    state = ctx.obj
    result = asyncio.run(transform_set(state.bridge, object_path, pos, rot, scl, local))
    print_result(result, state.formatter)


@transform_app.command("parent")
def transform_parent_cli(
    ctx: typer.Context,
    object_path: Annotated[str, typer.Argument(help="Hierarchy path to the GameObject.")],
    new_parent: Annotated[
        str | None,
        typer.Argument(help="Hierarchy path of new parent (omit to unparent)."),
    ] = None,
    world_position_stays: Annotated[
        bool,
        typer.Option(
            "--world-position-stays/--no-world-position-stays", help="Preserve world position."
        ),
    ] = True,
) -> None:
    """Reparent a GameObject."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        transform_parent(state.bridge, object_path, new_parent, world_position_stays)
    )
    print_result(result, state.formatter)


@transform_app.command("sibling-index")
def transform_sibling_index_cli(
    ctx: typer.Context,
    object_path: Annotated[str, typer.Argument(help="Hierarchy path to the GameObject.")],
    index: Annotated[int, typer.Argument(help="Target sibling index.")],
) -> None:
    """Set hierarchy order within parent."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(transform_sibling_index(state.bridge, object_path, index))
    print_result(result, state.formatter)

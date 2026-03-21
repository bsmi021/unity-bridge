"""Scene View camera control commands."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def scene_view_get(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """Get the current Scene View camera state.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="scene-view",
        parameters={"operation": "get-camera"},
        timeout=timeout,
    )


async def scene_view_set(
    bridge: DirectBridge,
    pivot: tuple[float, float, float] | None = None,
    rotation: tuple[float, float, float] | None = None,
    size: float | None = None,
    orthographic: bool | None = None,
    timeout: float = 10.0,
) -> CommandResult:
    """Set the Scene View camera transform.

    Args:
        bridge: Active bridge connection.
        pivot: Camera pivot point (x, y, z).
        rotation: Euler rotation (x, y, z).
        size: Camera orbit size.
        orthographic: True for orthographic, False for perspective.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {"operation": "set-camera"}

    if pivot is not None:
        params["pivot"] = {"x": pivot[0], "y": pivot[1], "z": pivot[2], "isSet": True}
    if rotation is not None:
        params["rotation"] = {
            "x": rotation[0],
            "y": rotation[1],
            "z": rotation[2],
            "isSet": True,
        }
    if size is not None:
        params["size"] = size
    if orthographic is True:
        params["orthographic"] = True
    elif orthographic is False:
        params["setPerspective"] = True

    return await bridge.send_command_with_retry(
        command_type="scene-view",
        parameters=params,
        timeout=timeout,
    )


async def scene_view_toggle_2d(
    bridge: DirectBridge,
    enable: bool = True,
    timeout: float = 10.0,
) -> CommandResult:
    """Toggle 2D mode on the Scene View.

    Args:
        bridge: Active bridge connection.
        enable: True to enable 2D, False to disable.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="scene-view",
        parameters={"operation": "toggle-2d", "enable2D": enable},
        timeout=timeout,
    )


async def scene_view_set_draw_mode(
    bridge: DirectBridge,
    draw_mode: str,
    timeout: float = 10.0,
) -> CommandResult:
    """Set the Scene View draw mode.

    Args:
        bridge: Active bridge connection.
        draw_mode: Draw mode name (Textured, Wireframe, etc.).
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="scene-view",
        parameters={"operation": "set-draw-mode", "drawMode": draw_mode},
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_xyz(raw: str) -> tuple[float, float, float]:
    """Parse 'X,Y,Z' string into a 3-tuple of floats."""
    parts = raw.split(",")
    if len(parts) != 3:
        raise typer.BadParameter(f"Expected X,Y,Z format, got: {raw}")
    return (float(parts[0]), float(parts[1]), float(parts[2]))


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

scene_view_app = typer.Typer(name="scene-view", help="Scene View camera control.")


@scene_view_app.command("get")
def scene_view_get_cli(ctx: typer.Context) -> None:
    """Get the current Scene View camera state."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(scene_view_get(state.bridge))
    print_result(result, state.formatter)


@scene_view_app.command("set")
def scene_view_set_cli(
    ctx: typer.Context,
    pivot: Annotated[
        str | None,
        typer.Option("--pivot", help="Pivot position as X,Y,Z."),
    ] = None,
    rotation: Annotated[
        str | None,
        typer.Option("--rotation", help="Euler rotation as X,Y,Z."),
    ] = None,
    size: Annotated[
        float | None,
        typer.Option("--size", help="Camera orbit size."),
    ] = None,
    orthographic: Annotated[
        bool | None,
        typer.Option("--ortho/--perspective", help="Orthographic or perspective."),
    ] = None,
) -> None:
    """Set the Scene View camera transform."""
    from unity_bridge.core.output import print_result

    parsed_pivot = _parse_xyz(pivot) if pivot else None
    parsed_rotation = _parse_xyz(rotation) if rotation else None

    state = ctx.obj
    result = asyncio.run(
        scene_view_set(state.bridge, parsed_pivot, parsed_rotation, size, orthographic)
    )
    print_result(result, state.formatter)


@scene_view_app.command("toggle-2d")
def scene_view_toggle_2d_cli(
    ctx: typer.Context,
    enable: Annotated[
        bool,
        typer.Option("--enable/--disable", help="Enable or disable 2D mode."),
    ] = True,
) -> None:
    """Toggle 2D mode on the Scene View."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(scene_view_toggle_2d(state.bridge, enable))
    print_result(result, state.formatter)


@scene_view_app.command("set-draw-mode")
def scene_view_set_draw_mode_cli(
    ctx: typer.Context,
    draw_mode: Annotated[
        str,
        typer.Argument(help="Draw mode: Textured, Wireframe, TexturedWire, etc."),
    ],
) -> None:
    """Set the Scene View draw mode."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(scene_view_set_draw_mode(state.bridge, draw_mode))
    print_result(result, state.formatter)

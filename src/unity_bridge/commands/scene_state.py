"""Deterministic Scene View and editor-state commands."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge


async def scene_state_operation(
    bridge: DirectBridge,
    operation: str,
    *,
    timeout: float = 10.0,
    **fields: object,
) -> CommandResult:
    """Run a scene-state bridge operation."""
    params: dict[str, object] = {"operation": operation}
    params.update({key: value for key, value in fields.items() if value is not None})
    return await bridge.send_command_with_retry(
        command_type="scene-state",
        parameters=params,
        timeout=timeout,
    )


async def scene_state_get(bridge: DirectBridge, timeout: float = 10.0) -> CommandResult:
    """Read deterministic Scene View/editor state."""
    return await scene_state_operation(bridge, "get", timeout=timeout)


async def scene_state_list_overlays(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """List active Scene View overlays."""
    return await scene_state_operation(bridge, "list-overlays", timeout=timeout)


async def scene_state_reset_snap(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """Reset Unity editor snap settings."""
    return await scene_state_operation(bridge, "reset-snap", timeout=timeout)


async def scene_state_set(
    bridge: DirectBridge,
    *,
    show_grid: bool | None = None,
    grid_snap_enabled: bool | None = None,
    snap_enabled: bool | None = None,
    angle_snap_enabled: bool | None = None,
    scale_snap_enabled: bool | None = None,
    grid_size: list[float] | None = None,
    grid_position: list[float] | None = None,
    move_snap: list[float] | None = None,
    rotate_snap: float | None = None,
    scale_snap: float | None = None,
    draw_gizmos: bool | None = None,
    use_3d_gizmos: bool | None = None,
    show_selection_outline: bool | None = None,
    show_selection_wire: bool | None = None,
    active_tool: str | None = None,
    pivot_mode: str | None = None,
    pivot_rotation: str | None = None,
    tools_hidden: bool | None = None,
    visible_layers: int | None = None,
    locked_layers: int | None = None,
    overlays_enabled: bool | None = None,
    timeout: float = 10.0,
) -> CommandResult:
    """Set supplied deterministic Scene View/editor state fields."""
    return await scene_state_operation(
        bridge,
        "set",
        timeout=timeout,
        showGrid=show_grid,
        gridSnapEnabled=grid_snap_enabled,
        snapEnabled=snap_enabled,
        angleSnapEnabled=angle_snap_enabled,
        scaleSnapEnabled=scale_snap_enabled,
        gridSize=grid_size,
        gridPosition=grid_position,
        moveSnap=move_snap,
        rotateSnap=rotate_snap,
        scaleSnap=scale_snap,
        drawGizmos=draw_gizmos,
        use3dGizmos=use_3d_gizmos,
        showSelectionOutline=show_selection_outline,
        showSelectionWire=show_selection_wire,
        activeTool=active_tool,
        pivotMode=pivot_mode,
        pivotRotation=pivot_rotation,
        toolsHidden=tools_hidden,
        visibleLayers=visible_layers,
        lockedLayers=locked_layers,
        overlaysEnabled=overlays_enabled,
    )


scene_state_app = typer.Typer(name="scene-state", help="Scene View/editor state.")


def _parse_vec3(value: str | None) -> list[float] | None:
    if value is None:
        return None
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 3:
        raise typer.BadParameter("Expected x,y,z")
    return [float(part) for part in parts]


@scene_state_app.command("get")
def get_cli(ctx: typer.Context) -> None:
    """Read deterministic Scene View/editor state."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    print_result(asyncio.run(scene_state_get(state.bridge)), state.formatter)


@scene_state_app.command("list-overlays")
def list_overlays_cli(ctx: typer.Context) -> None:
    """List active Scene View overlays."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    print_result(asyncio.run(scene_state_list_overlays(state.bridge)), state.formatter)


@scene_state_app.command("reset-snap")
def reset_snap_cli(ctx: typer.Context) -> None:
    """Reset Unity editor snap settings."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    print_result(asyncio.run(scene_state_reset_snap(state.bridge)), state.formatter)


@scene_state_app.command("set")
def set_cli(
    ctx: typer.Context,
    show_grid: Annotated[bool | None, typer.Option("--show-grid/--hide-grid")] = None,
    grid_snap: Annotated[bool | None, typer.Option("--grid-snap/--no-grid-snap")] = None,
    snap: Annotated[bool | None, typer.Option("--snap/--no-snap")] = None,
    grid_size: Annotated[str | None, typer.Option("--grid-size")] = None,
    move_snap: Annotated[str | None, typer.Option("--move-snap")] = None,
    active_tool: Annotated[str | None, typer.Option("--tool")] = None,
    overlays: Annotated[bool | None, typer.Option("--overlays/--no-overlays")] = None,
) -> None:
    """Set common deterministic Scene View/editor state fields."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        scene_state_set(
            state.bridge,
            show_grid=show_grid,
            grid_snap_enabled=grid_snap,
            snap_enabled=snap,
            grid_size=_parse_vec3(grid_size),
            move_snap=_parse_vec3(move_snap),
            active_tool=active_tool,
            overlays_enabled=overlays,
        )
    )
    print_result(result, state.formatter)

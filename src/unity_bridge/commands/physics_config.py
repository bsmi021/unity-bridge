"""Physics configuration commands: get, set, collision matrix."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_gravity(value: str) -> tuple[float, float, float]:
    """Parse 'X,Y,Z' gravity string."""
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


async def physics_get(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """Get current physics settings.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="physics-config",
        parameters={"operation": "get"},
        timeout=timeout,
    )


async def physics_set(
    bridge: DirectBridge,
    gravity: tuple[float, float, float] | None = None,
    solver_iterations: int | None = None,
    bounce_threshold: float | None = None,
    sleep_threshold: float | None = None,
    default_contact_offset: float | None = None,
    auto_sync_transforms: bool | None = None,
    reuse_collision_callbacks: bool | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Set physics configuration values.

    Args:
        bridge: Active bridge connection.
        gravity: World gravity as (x, y, z).
        solver_iterations: Default solver iteration count.
        bounce_threshold: Bounce threshold velocity.
        sleep_threshold: Sleep threshold energy.
        default_contact_offset: Default contact offset.
        auto_sync_transforms: Auto-sync transforms.
        reuse_collision_callbacks: Reuse collision callbacks.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {"operation": "set"}

    if gravity is not None:
        params["gravity"] = {"x": gravity[0], "y": gravity[1], "z": gravity[2], "isSet": True}
    if solver_iterations is not None:
        params["defaultSolverIterations"] = solver_iterations
    if bounce_threshold is not None:
        params["bounceThreshold"] = bounce_threshold
    if sleep_threshold is not None:
        params["sleepThreshold"] = sleep_threshold
    if default_contact_offset is not None:
        params["defaultContactOffset"] = default_contact_offset
    if auto_sync_transforms is not None:
        params["autoSyncTransforms"] = auto_sync_transforms
        params["setAutoSyncTransforms"] = True
    if reuse_collision_callbacks is not None:
        params["reuseCollisionCallbacks"] = reuse_collision_callbacks
        params["setReuseCollisionCallbacks"] = True

    return await bridge.send_command_with_retry(
        command_type="physics-config",
        parameters=params,
        timeout=timeout,
    )


async def physics_collision_get(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """Get the layer collision matrix.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="physics-config",
        parameters={"operation": "collision-matrix-get"},
        timeout=timeout,
    )


async def physics_collision_set(
    bridge: DirectBridge,
    layer1: int,
    layer2: int,
    ignore: bool = False,
    timeout: float = 15.0,
) -> CommandResult:
    """Set collision between two layers.

    Args:
        bridge: Active bridge connection.
        layer1: First layer index (0-31).
        layer2: Second layer index (0-31).
        ignore: True to ignore collisions, False to enable.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="physics-config",
        parameters={
            "operation": "collision-matrix-set",
            "layer1": layer1,
            "layer2": layer2,
            "ignoreCollision": ignore,
        },
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

physics_app = typer.Typer(name="physics", help="Physics configuration commands.")


@physics_app.command("get")
def physics_get_cli(ctx: typer.Context) -> None:
    """Get current physics settings."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(physics_get(state.bridge))
    print_result(result, state.formatter)


@physics_app.command("set")
def physics_set_cli(
    ctx: typer.Context,
    gravity: Annotated[
        str | None,
        typer.Option("--gravity", "-g", help="Gravity as X,Y,Z (e.g. 0,-9.81,0)."),
    ] = None,
    solver_iterations: Annotated[
        int | None,
        typer.Option("--solver-iterations", help="Default solver iterations."),
    ] = None,
) -> None:
    """Set physics configuration values."""
    from unity_bridge.core.output import print_result

    grav = _parse_gravity(gravity) if gravity else None
    state = ctx.obj
    result = asyncio.run(
        physics_set(state.bridge, gravity=grav, solver_iterations=solver_iterations)
    )
    print_result(result, state.formatter)


# -- Collision sub-group ---------------------------------------------------

collision_app = typer.Typer(name="collision", help="Layer collision matrix commands.")
physics_app.add_typer(collision_app, name="collision")


@collision_app.command("get")
def collision_get_cli(ctx: typer.Context) -> None:
    """Get the layer collision matrix."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(physics_collision_get(state.bridge))
    print_result(result, state.formatter)


@collision_app.command("set")
def collision_set_cli(
    ctx: typer.Context,
    layer1: Annotated[int, typer.Argument(help="First layer index (0-31).")],
    layer2: Annotated[int, typer.Argument(help="Second layer index (0-31).")],
    ignore: Annotated[
        bool,
        typer.Option("--ignore/--collide", help="Ignore or enable collisions."),
    ] = False,
) -> None:
    """Set collision between two layers."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(physics_collision_set(state.bridge, layer1, layer2, ignore))
    print_result(result, state.formatter)

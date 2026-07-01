"""Physics2D settings and the 2D layer collision matrix.

Symmetric with ``physics_config`` but operates on the ``Physics2D`` API
surface and the 2D collision matrix.
"""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge
from unity_bridge.core.settings_params import SettingField, build_set_params

_PHYSICS2D_FIELDS = [
    SettingField("gravity", ("gravityX", "gravityY"), "setGravity"),
    SettingField("velocity_iterations", ("velocityIterations",), "setVelocityIterations"),
    SettingField("position_iterations", ("positionIterations",), "setPositionIterations"),
    SettingField("velocity_threshold", ("velocityThreshold",), "setVelocityThreshold"),
    SettingField(
        "default_contact_offset", ("defaultContactOffset",), "setDefaultContactOffset"
    ),
    SettingField("queries_hit_triggers", ("queriesHitTriggers",), "setQueriesHitTriggers"),
    SettingField("auto_sync_transforms", ("autoSyncTransforms",), "setAutoSyncTransforms"),
]


async def physics2d_get(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """Read all Physics2D settings."""
    return await bridge.send_command_with_retry(
        command_type="physics2d-config",
        parameters={"operation": "get"},
        timeout=timeout,
    )


async def physics2d_set(
    bridge: DirectBridge,
    *,
    gravity: tuple[float, float] | None = None,
    velocity_iterations: int | None = None,
    position_iterations: int | None = None,
    velocity_threshold: float | None = None,
    default_contact_offset: float | None = None,
    queries_hit_triggers: bool | None = None,
    auto_sync_transforms: bool | None = None,
    timeout: float = 10.0,
) -> CommandResult:
    """Mutate selected Physics2D properties. Only provided fields change."""
    params = build_set_params("set", _PHYSICS2D_FIELDS, locals())
    return await bridge.send_command_with_retry(
        command_type="physics2d-config",
        parameters=params,
        timeout=timeout,
    )


async def physics2d_get_matrix(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """Read the 32x32 2D layer collision matrix."""
    return await bridge.send_command_with_retry(
        command_type="physics2d-config",
        parameters={"operation": "get-collision-matrix"},
        timeout=timeout,
    )


async def physics2d_set_collision(
    bridge: DirectBridge,
    layer_a: int,
    layer_b: int,
    collides: bool,
    timeout: float = 10.0,
) -> CommandResult:
    """Toggle collision between two 2D physics layers (0-31 each)."""
    return await bridge.send_command_with_retry(
        command_type="physics2d-config",
        parameters={
            "operation": "set-collision",
            "layerA": layer_a,
            "layerB": layer_b,
            "collides": collides,
        },
        timeout=timeout,
    )


physics2d_app = typer.Typer(
    name="physics2d",
    help="Physics2D settings and 2D layer collision matrix.",
)


@physics2d_app.command("get")
def get_cli(ctx: typer.Context) -> None:
    """Read all Physics2D settings."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(physics2d_get(state.bridge))
    print_result(result, state.formatter)


@physics2d_app.command("set")
def set_cli(
    ctx: typer.Context,
    gravity: Annotated[
        str | None,
        typer.Option("--gravity", help="Gravity as 'X,Y' (e.g. '0,-9.81')."),
    ] = None,
    velocity_iterations: Annotated[
        int | None, typer.Option("--velocity-iterations")
    ] = None,
    position_iterations: Annotated[
        int | None, typer.Option("--position-iterations")
    ] = None,
    velocity_threshold: Annotated[
        float | None, typer.Option("--velocity-threshold")
    ] = None,
    default_contact_offset: Annotated[
        float | None, typer.Option("--default-contact-offset")
    ] = None,
    queries_hit_triggers: Annotated[
        bool | None, typer.Option("--queries-hit-triggers/--no-queries-hit-triggers")
    ] = None,
    auto_sync_transforms: Annotated[
        bool | None, typer.Option("--auto-sync-transforms/--no-auto-sync-transforms")
    ] = None,
) -> None:
    """Mutate one or more Physics2D fields."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    gravity_tuple: tuple[float, float] | None = None
    if gravity is not None:
        try:
            x, y = gravity.split(",")
            gravity_tuple = (float(x), float(y))
        except ValueError as exc:
            raise typer.BadParameter("--gravity must be 'X,Y'") from exc

    result = asyncio.run(
        physics2d_set(
            state.bridge,
            gravity=gravity_tuple,
            velocity_iterations=velocity_iterations,
            position_iterations=position_iterations,
            velocity_threshold=velocity_threshold,
            default_contact_offset=default_contact_offset,
            queries_hit_triggers=queries_hit_triggers,
            auto_sync_transforms=auto_sync_transforms,
        )
    )
    print_result(result, state.formatter)


@physics2d_app.command("matrix")
def matrix_cli(ctx: typer.Context) -> None:
    """Read the 2D layer collision matrix."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(physics2d_get_matrix(state.bridge))
    print_result(result, state.formatter)


@physics2d_app.command("set-collision")
def set_collision_cli(
    ctx: typer.Context,
    layer_a: Annotated[int, typer.Argument(help="First layer index (0-31).")],
    layer_b: Annotated[int, typer.Argument(help="Second layer index (0-31).")],
    collides: Annotated[
        bool,
        typer.Option("--collides/--no-collides", help="Whether the layers collide."),
    ] = True,
) -> None:
    """Toggle 2D collision between two layers."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(physics2d_set_collision(state.bridge, layer_a, layer_b, collides))
    print_result(result, state.formatter)

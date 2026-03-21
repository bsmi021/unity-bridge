"""NavMesh commands: bake, clear, settings, areas."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def navmesh_bake(
    bridge: DirectBridge,
    timeout: float = 60.0,
) -> CommandResult:
    """Bake NavMesh for the active scene.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="navmesh-operation",
        parameters={"operation": "bake"},
        timeout=timeout,
    )


async def navmesh_clear(
    bridge: DirectBridge,
    timeout: float = 30.0,
) -> CommandResult:
    """Clear all baked NavMesh data.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="navmesh-operation",
        parameters={"operation": "clear"},
        timeout=timeout,
    )


async def navmesh_get_settings(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """Get current NavMesh build settings.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="navmesh-operation",
        parameters={"operation": "get-settings"},
        timeout=timeout,
    )


async def navmesh_set_settings(
    bridge: DirectBridge,
    agent_radius: float | None = None,
    agent_height: float | None = None,
    max_slope: float | None = None,
    step_height: float | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Set NavMesh build settings.

    Args:
        bridge: Active bridge connection.
        agent_radius: Agent radius.
        agent_height: Agent height.
        max_slope: Maximum slope angle in degrees.
        step_height: Maximum step height.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {"operation": "set-settings"}
    if agent_radius is not None:
        params["agentRadius"] = agent_radius
    if agent_height is not None:
        params["agentHeight"] = agent_height
    if max_slope is not None:
        params["agentSlope"] = max_slope
    if step_height is not None:
        params["agentClimb"] = step_height

    return await bridge.send_command_with_retry(
        command_type="navmesh-operation",
        parameters=params,
        timeout=timeout,
    )


async def navmesh_get_areas(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """Get NavMesh area names and costs.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="navmesh-operation",
        parameters={"operation": "get-areas"},
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

navmesh_app = typer.Typer(name="navmesh", help="NavMesh baking and settings commands.")


@navmesh_app.command("bake")
def navmesh_bake_cli(ctx: typer.Context) -> None:
    """Bake NavMesh for the active scene."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(navmesh_bake(state.bridge))
    print_result(result, state.formatter)


@navmesh_app.command("clear")
def navmesh_clear_cli(ctx: typer.Context) -> None:
    """Clear all baked NavMesh data."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(navmesh_clear(state.bridge))
    print_result(result, state.formatter)


@navmesh_app.command("settings")
def navmesh_settings_cli(
    ctx: typer.Context,
    agent_radius: Annotated[
        float | None,
        typer.Option("--agent-radius", help="Agent radius."),
    ] = None,
    agent_height: Annotated[
        float | None,
        typer.Option("--agent-height", help="Agent height."),
    ] = None,
    max_slope: Annotated[
        float | None,
        typer.Option("--max-slope", help="Maximum slope angle."),
    ] = None,
    step_height: Annotated[
        float | None,
        typer.Option("--step-height", help="Maximum step height."),
    ] = None,
) -> None:
    """Get or set NavMesh build settings (get if no options)."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    if any(v is not None for v in (agent_radius, agent_height, max_slope, step_height)):
        result = asyncio.run(
            navmesh_set_settings(
                state.bridge,
                agent_radius=agent_radius,
                agent_height=agent_height,
                max_slope=max_slope,
                step_height=step_height,
            )
        )
    else:
        result = asyncio.run(navmesh_get_settings(state.bridge))
    print_result(result, state.formatter)


@navmesh_app.command("areas")
def navmesh_areas_cli(ctx: typer.Context) -> None:
    """Get NavMesh area names and costs."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(navmesh_get_areas(state.bridge))
    print_result(result, state.formatter)

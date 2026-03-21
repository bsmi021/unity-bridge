"""Time settings commands: get and set Unity Time properties."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def time_get(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """Get current time settings.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="time-settings",
        parameters={"operation": "get"},
        timeout=timeout,
    )


async def time_set(
    bridge: DirectBridge,
    fixed_delta: float | None = None,
    maximum_delta: float | None = None,
    time_scale: float | None = None,
    max_particle_delta: float | None = None,
    capture_delta: float | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Set time configuration values.

    Args:
        bridge: Active bridge connection.
        fixed_delta: Fixed timestep (default 0.02).
        maximum_delta: Maximum allowed timestep.
        time_scale: Time scale factor (1.0 = normal).
        max_particle_delta: Maximum particle timestep.
        capture_delta: Capture framerate timestep (0 = variable).
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {"operation": "set"}

    if fixed_delta is not None:
        params["fixedDeltaTime"] = fixed_delta
        params["setFixedDeltaTime"] = True
    if maximum_delta is not None:
        params["maximumDeltaTime"] = maximum_delta
        params["setMaximumDeltaTime"] = True
    if time_scale is not None:
        params["timeScale"] = time_scale
        params["setTimeScale"] = True
    if max_particle_delta is not None:
        params["maximumParticleDeltaTime"] = max_particle_delta
        params["setMaximumParticleDeltaTime"] = True
    if capture_delta is not None:
        params["captureDeltaTime"] = capture_delta
        params["setCaptureDeltaTime"] = True

    return await bridge.send_command_with_retry(
        command_type="time-settings",
        parameters=params,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

time_app = typer.Typer(name="time", help="Unity Time settings commands.")


@time_app.command("get")
def time_get_cli(ctx: typer.Context) -> None:
    """Get current time settings."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(time_get(state.bridge))
    print_result(result, state.formatter)


@time_app.command("set")
def time_set_cli(
    ctx: typer.Context,
    fixed_delta: Annotated[
        float | None,
        typer.Option("--fixed-delta", help="Fixed timestep (e.g. 0.02)."),
    ] = None,
    time_scale: Annotated[
        float | None,
        typer.Option("--time-scale", help="Time scale factor (1.0 = normal)."),
    ] = None,
    maximum_delta: Annotated[
        float | None,
        typer.Option("--max-delta", help="Maximum allowed timestep."),
    ] = None,
    max_particle_delta: Annotated[
        float | None,
        typer.Option("--max-particle-delta", help="Maximum particle timestep."),
    ] = None,
    capture_delta: Annotated[
        float | None,
        typer.Option("--capture-delta", help="Capture framerate timestep."),
    ] = None,
) -> None:
    """Set time configuration values."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        time_set(
            state.bridge,
            fixed_delta=fixed_delta,
            maximum_delta=maximum_delta,
            time_scale=time_scale,
            max_particle_delta=max_particle_delta,
            capture_delta=capture_delta,
        )
    )
    print_result(result, state.formatter)

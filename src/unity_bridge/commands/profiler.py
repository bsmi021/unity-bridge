"""Profiler advanced control commands."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def profiler_start(
    bridge: DirectBridge,
    log_file: str | None = None,
    timeout: float = 10.0,
) -> CommandResult:
    """Start the Unity Profiler.

    Args:
        bridge: Active bridge connection.
        log_file: Optional path to save profiler data.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {"operation": "start"}
    if log_file is not None:
        params["logFile"] = log_file

    return await bridge.send_command_with_retry(
        command_type="profiler-control",
        parameters=params,
        timeout=timeout,
    )


async def profiler_stop(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """Stop the Unity Profiler.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="profiler-control",
        parameters={"operation": "stop"},
        timeout=timeout,
    )


async def profiler_save(
    bridge: DirectBridge,
    log_file: str,
    timeout: float = 10.0,
) -> CommandResult:
    """Save profiler data to a file.

    Args:
        bridge: Active bridge connection.
        log_file: Path to save profiler data.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="profiler-control",
        parameters={"operation": "save", "logFile": log_file},
        timeout=timeout,
    )


async def profiler_memory(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """Get detailed memory statistics from the profiler.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="profiler-control",
        parameters={"operation": "memory"},
        timeout=timeout,
    )


async def profiler_set_areas(
    bridge: DirectBridge,
    *,
    areas: list[str],
    enabled: bool = True,
    allocation_callstacks: bool | None = None,
    timeout: float = 10.0,
) -> CommandResult:
    """Enable or disable profiler areas and optional allocation callstacks."""
    params: dict[str, object] = {
        "operation": "set-areas",
        "areas": ",".join(areas),
        "enabled": enabled,
    }
    if allocation_callstacks is not None:
        params["allocationCallstacks"] = allocation_callstacks
    return await bridge.send_command_with_retry(
        command_type="profiler-control",
        parameters=params,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

profiler_app = typer.Typer(name="profiler", help="Profiler advanced controls.")


@profiler_app.command("start")
def profiler_start_cli(
    ctx: typer.Context,
    log_file: Annotated[
        str | None,
        typer.Option("--log-file", help="Path to save profiler data."),
    ] = None,
) -> None:
    """Start the Unity Profiler."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(profiler_start(state.bridge, log_file))
    print_result(result, state.formatter)


@profiler_app.command("stop")
def profiler_stop_cli(ctx: typer.Context) -> None:
    """Stop the Unity Profiler."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(profiler_stop(state.bridge))
    print_result(result, state.formatter)


@profiler_app.command("save")
def profiler_save_cli(
    ctx: typer.Context,
    log_file: Annotated[str, typer.Argument(help="Path to save profiler data.")],
) -> None:
    """Save profiler data to a file."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(profiler_save(state.bridge, log_file))
    print_result(result, state.formatter)


@profiler_app.command("memory")
def profiler_memory_cli(ctx: typer.Context) -> None:
    """Get detailed memory statistics."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(profiler_memory(state.bridge))
    print_result(result, state.formatter)


@profiler_app.command("set-areas")
def profiler_set_areas_cli(
    ctx: typer.Context,
    areas: Annotated[
        str,
        typer.Option("--areas", help="Comma-separated profiler areas."),
    ],
    enabled: Annotated[
        bool,
        typer.Option("--enabled/--disabled", help="Enable or disable areas."),
    ] = True,
    allocation_callstacks: Annotated[
        bool | None,
        typer.Option("--allocation-callstacks/--no-allocation-callstacks"),
    ] = None,
) -> None:
    """Enable or disable profiler areas."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    area_list = [area.strip() for area in areas.split(",") if area.strip()]
    result = asyncio.run(
        profiler_set_areas(
            state.bridge,
            areas=area_list,
            enabled=enabled,
            allocation_callstacks=allocation_callstacks,
        )
    )
    print_result(result, state.formatter)

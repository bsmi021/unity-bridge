"""Reflection probe commands: bake, bake-all, list, get-info."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def reflection_probe_bake(
    bridge: DirectBridge,
    game_object_path: str,
    timeout: float = 30.0,
) -> CommandResult:
    """Bake a single reflection probe.

    Args:
        bridge: Active bridge connection.
        game_object_path: Hierarchy path to the probe.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="reflection-probe",
        parameters={"operation": "bake", "gameObjectPath": game_object_path},
        timeout=timeout,
    )


async def reflection_probe_bake_all(
    bridge: DirectBridge,
    timeout: float = 60.0,
) -> CommandResult:
    """Bake all reflection probes in the scene.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="reflection-probe",
        parameters={"operation": "bake-all"},
        timeout=timeout,
    )


async def reflection_probe_list(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """List all reflection probes in the scene.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="reflection-probe",
        parameters={"operation": "list"},
        timeout=timeout,
    )


async def reflection_probe_get_info(
    bridge: DirectBridge,
    game_object_path: str,
    timeout: float = 10.0,
) -> CommandResult:
    """Get reflection probe info.

    Args:
        bridge: Active bridge connection.
        game_object_path: Hierarchy path to the probe.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="reflection-probe",
        parameters={"operation": "get-info", "gameObjectPath": game_object_path},
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

reflection_probes_app = typer.Typer(name="reflection-probes", help="Reflection probe commands.")


@reflection_probes_app.command("bake")
def reflection_bake_cli(
    ctx: typer.Context,
    game_object_path: Annotated[
        str | None,
        typer.Argument(help="Hierarchy path to probe. Omit with --all to bake all."),
    ] = None,
    all_probes: Annotated[
        bool,
        typer.Option("--all", help="Bake all probes in scene."),
    ] = False,
) -> None:
    """Bake reflection probe(s)."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    if all_probes:
        result = asyncio.run(reflection_probe_bake_all(state.bridge))
    elif game_object_path:
        result = asyncio.run(reflection_probe_bake(state.bridge, game_object_path))
    else:
        result = asyncio.run(reflection_probe_bake_all(state.bridge))
    print_result(result, state.formatter)


@reflection_probes_app.command("list")
def reflection_list_cli(ctx: typer.Context) -> None:
    """List all reflection probes in the scene."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(reflection_probe_list(state.bridge))
    print_result(result, state.formatter)


@reflection_probes_app.command("info")
def reflection_info_cli(
    ctx: typer.Context,
    game_object_path: Annotated[str, typer.Argument(help="Hierarchy path to the probe.")],
) -> None:
    """Get reflection probe info."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(reflection_probe_get_info(state.bridge, game_object_path))
    print_result(result, state.formatter)

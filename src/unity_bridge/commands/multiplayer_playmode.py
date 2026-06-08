"""Read-only Multiplayer Play Mode bridge commands."""

from __future__ import annotations

import asyncio

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge


async def multiplayer_playmode_operation(
    bridge: DirectBridge,
    operation: str,
    *,
    timeout: float = 15.0,
) -> CommandResult:
    """Run a Multiplayer Play Mode bridge operation."""
    return await bridge.send_command_with_retry(
        command_type="multiplayer-playmode",
        parameters={"operation": operation},
        timeout=timeout,
    )


async def multiplayer_playmode_availability(
    bridge: DirectBridge,
    timeout: float = 15.0,
) -> CommandResult:
    """Check Multiplayer Play Mode package/API availability."""
    return await multiplayer_playmode_operation(bridge, "availability", timeout=timeout)


async def multiplayer_playmode_current_player(
    bridge: DirectBridge,
    timeout: float = 15.0,
) -> CommandResult:
    """Read the current Multiplayer Play Mode player context."""
    return await multiplayer_playmode_operation(bridge, "current-player", timeout=timeout)


async def multiplayer_playmode_packages(
    bridge: DirectBridge,
    timeout: float = 15.0,
) -> CommandResult:
    """List Multiplayer Play Mode related package information."""
    return await multiplayer_playmode_operation(bridge, "packages", timeout=timeout)


multiplayer_playmode_app = typer.Typer(
    name="multiplayer-playmode",
    help="Read-only Multiplayer Play Mode inspection.",
)


@multiplayer_playmode_app.command("availability")
def availability_cli(ctx: typer.Context) -> None:
    """Check Multiplayer Play Mode availability."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    print_result(asyncio.run(multiplayer_playmode_availability(state.bridge)), state.formatter)


@multiplayer_playmode_app.command("current-player")
def current_player_cli(ctx: typer.Context) -> None:
    """Read current Multiplayer Play Mode player context."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    print_result(asyncio.run(multiplayer_playmode_current_player(state.bridge)), state.formatter)


@multiplayer_playmode_app.command("packages")
def packages_cli(ctx: typer.Context) -> None:
    """List Multiplayer Play Mode package information."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    print_result(asyncio.run(multiplayer_playmode_packages(state.bridge)), state.formatter)

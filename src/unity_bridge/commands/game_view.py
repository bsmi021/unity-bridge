"""Game View configuration commands."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def game_view_get(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """Get the current Game View state.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="game-view",
        parameters={"operation": "get"},
        timeout=timeout,
    )


async def game_view_set_resolution(
    bridge: DirectBridge,
    width: int,
    height: int,
    timeout: float = 10.0,
) -> CommandResult:
    """Set the Game View resolution.

    Args:
        bridge: Active bridge connection.
        width: Resolution width in pixels.
        height: Resolution height in pixels.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="game-view",
        parameters={
            "operation": "set-resolution",
            "width": width,
            "height": height,
        },
        timeout=timeout,
    )


async def game_view_set_scale(
    bridge: DirectBridge,
    scale: float,
    timeout: float = 10.0,
) -> CommandResult:
    """Set the Game View zoom scale.

    Args:
        bridge: Active bridge connection.
        scale: Zoom scale (1.0 = 100%).
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="game-view",
        parameters={
            "operation": "set-scale",
            "scale": scale,
        },
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

game_view_app = typer.Typer(name="game-view", help="Game View configuration.")


@game_view_app.command("get")
def game_view_get_cli(ctx: typer.Context) -> None:
    """Get the current Game View state."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(game_view_get(state.bridge))
    print_result(result, state.formatter)


@game_view_app.command("set-resolution")
def game_view_set_resolution_cli(
    ctx: typer.Context,
    width: Annotated[int, typer.Argument(help="Resolution width.")],
    height: Annotated[int, typer.Argument(help="Resolution height.")],
) -> None:
    """Set the Game View resolution."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(game_view_set_resolution(state.bridge, width, height))
    print_result(result, state.formatter)


@game_view_app.command("set-scale")
def game_view_set_scale_cli(
    ctx: typer.Context,
    scale: Annotated[float, typer.Argument(help="Zoom scale (1.0 = 100%).")],
) -> None:
    """Set the Game View zoom scale."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(game_view_set_scale(state.bridge, scale))
    print_result(result, state.formatter)

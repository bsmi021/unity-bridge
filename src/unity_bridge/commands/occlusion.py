"""Occlusion culling commands: bake, clear, settings."""

from __future__ import annotations

import asyncio

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def occlusion_bake(
    bridge: DirectBridge,
    timeout: float = 120.0,
) -> CommandResult:
    """Compute occlusion culling data.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="occlusion-culling",
        parameters={"operation": "bake"},
        timeout=timeout,
    )


async def occlusion_clear(
    bridge: DirectBridge,
    timeout: float = 30.0,
) -> CommandResult:
    """Clear occlusion culling data.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="occlusion-culling",
        parameters={"operation": "clear"},
        timeout=timeout,
    )


async def occlusion_get_settings(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """Get occlusion culling settings.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="occlusion-culling",
        parameters={"operation": "get-settings"},
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

occlusion_app = typer.Typer(name="occlusion", help="Occlusion culling commands.")


@occlusion_app.command("bake")
def occlusion_bake_cli(ctx: typer.Context) -> None:
    """Compute occlusion culling data."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(occlusion_bake(state.bridge))
    print_result(result, state.formatter)


@occlusion_app.command("clear")
def occlusion_clear_cli(ctx: typer.Context) -> None:
    """Clear occlusion culling data."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(occlusion_clear(state.bridge))
    print_result(result, state.formatter)


@occlusion_app.command("settings")
def occlusion_settings_cli(ctx: typer.Context) -> None:
    """Get occlusion culling settings."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(occlusion_get_settings(state.bridge))
    print_result(result, state.formatter)

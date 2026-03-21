"""Quality settings commands: list, get, set-level."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def quality_list(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """List all quality levels.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="quality-settings",
        parameters={"operation": "list"},
        timeout=timeout,
    )


async def quality_get(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """Get current quality settings.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="quality-settings",
        parameters={"operation": "get"},
        timeout=timeout,
    )


async def quality_set_level(
    bridge: DirectBridge,
    level: int,
    timeout: float = 15.0,
) -> CommandResult:
    """Switch active quality level.

    Args:
        bridge: Active bridge connection.
        level: Quality level index.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="quality-settings",
        parameters={"operation": "set-level", "level": level},
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

quality_app = typer.Typer(name="quality", help="Quality settings commands.")


@quality_app.command("list")
def quality_list_cli(ctx: typer.Context) -> None:
    """List all quality levels."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(quality_list(state.bridge))
    print_result(result, state.formatter)


@quality_app.command("get")
def quality_get_cli(ctx: typer.Context) -> None:
    """Get current quality settings."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(quality_get(state.bridge))
    print_result(result, state.formatter)


@quality_app.command("set-level")
def quality_set_level_cli(
    ctx: typer.Context,
    level: Annotated[int, typer.Argument(help="Quality level index.")],
) -> None:
    """Switch active quality level."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(quality_set_level(state.bridge, level))
    print_result(result, state.formatter)

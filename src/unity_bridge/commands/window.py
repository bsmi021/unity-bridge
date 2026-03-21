"""Window management commands: list, open, focus, close editor windows."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def window_list(
    bridge: DirectBridge,
    timeout: float = 5.0,
) -> CommandResult:
    """List all open editor windows.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="window-management",
        parameters={"operation": "list"},
        timeout=timeout,
    )


async def window_open(
    bridge: DirectBridge,
    window_name: str,
    timeout: float = 10.0,
) -> CommandResult:
    """Open an editor window by name.

    Args:
        bridge: Active bridge connection.
        window_name: Window name (Scene, Game, Inspector, Console, etc.).
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="window-management",
        parameters={"operation": "open", "windowName": window_name},
        timeout=timeout,
    )


async def window_focus(
    bridge: DirectBridge,
    window_name: str,
    timeout: float = 5.0,
) -> CommandResult:
    """Focus an existing editor window.

    Args:
        bridge: Active bridge connection.
        window_name: Window name to focus.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="window-management",
        parameters={"operation": "focus", "windowName": window_name},
        timeout=timeout,
    )


async def window_close(
    bridge: DirectBridge,
    window_name: str,
    timeout: float = 5.0,
) -> CommandResult:
    """Close an editor window.

    Args:
        bridge: Active bridge connection.
        window_name: Window name to close.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="window-management",
        parameters={"operation": "close", "windowName": window_name},
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrapper
# ---------------------------------------------------------------------------

window_app = typer.Typer(name="window", help="Unity Editor window management.")


@window_app.command("list")
def window_list_cli(ctx: typer.Context) -> None:
    """List all open editor windows."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(window_list(state.bridge))
    print_result(result, state.formatter)


@window_app.command("open")
def window_open_cli(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Window name (Scene, Inspector, Console, etc.).")],
) -> None:
    """Open an editor window."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(window_open(state.bridge, name))
    print_result(result, state.formatter)


@window_app.command("focus")
def window_focus_cli(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Window name to focus.")],
) -> None:
    """Focus an existing editor window."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(window_focus(state.bridge, name))
    print_result(result, state.formatter)


@window_app.command("close")
def window_close_cli(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Window name to close.")],
) -> None:
    """Close an editor window."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(window_close(state.bridge, name))
    print_result(result, state.formatter)

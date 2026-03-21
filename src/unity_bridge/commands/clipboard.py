"""Clipboard commands: read and write system clipboard via Unity Editor."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def clipboard_read(
    bridge: DirectBridge,
    timeout: float = 5.0,
) -> CommandResult:
    """Read the current system clipboard text.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="clipboard",
        parameters={"operation": "read"},
        timeout=timeout,
    )


async def clipboard_write(
    bridge: DirectBridge,
    text: str,
    timeout: float = 5.0,
) -> CommandResult:
    """Write text to the system clipboard.

    Args:
        bridge: Active bridge connection.
        text: Text to write to clipboard.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="clipboard",
        parameters={"operation": "write", "text": text},
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrapper
# ---------------------------------------------------------------------------

clipboard_app = typer.Typer(name="clipboard", help="System clipboard access via Unity Editor.")


@clipboard_app.command("read")
def clipboard_read_cli(ctx: typer.Context) -> None:
    """Read the current clipboard contents."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(clipboard_read(state.bridge))
    print_result(result, state.formatter)


@clipboard_app.command("write")
def clipboard_write_cli(
    ctx: typer.Context,
    text: Annotated[str, typer.Argument(help="Text to write to clipboard.")],
) -> None:
    """Write text to the clipboard."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(clipboard_write(state.bridge, text))
    print_result(result, state.formatter)

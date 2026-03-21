"""Editor configuration commands: get, set."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def editor_config_get(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """Get current editor settings.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="editor-config",
        parameters={"operation": "get"},
        timeout=timeout,
    )


async def editor_config_set(
    bridge: DirectBridge,
    key: str,
    value: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Set an editor configuration value.

    Args:
        bridge: Active bridge connection.
        key: Setting key (e.g. serializationMode, asyncShaderCompilation).
        value: New value as string.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="editor-config",
        parameters={"operation": "set", "key": key, "value": value},
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

editor_config_app = typer.Typer(name="editor-config", help="Editor configuration commands.")


@editor_config_app.command("get")
def editor_config_get_cli(ctx: typer.Context) -> None:
    """Get current editor settings."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(editor_config_get(state.bridge))
    print_result(result, state.formatter)


@editor_config_app.command("set")
def editor_config_set_cli(
    ctx: typer.Context,
    key: Annotated[str, typer.Argument(help="Setting key.")],
    value: Annotated[str, typer.Argument(help="New value.")],
) -> None:
    """Set an editor configuration value."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(editor_config_set(state.bridge, key, value))
    print_result(result, state.formatter)

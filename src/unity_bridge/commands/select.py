"""Selection commands: set and clear editor selection."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def set_selection(
    bridge: DirectBridge,
    game_object_paths: list[str],
    timeout: float = 5.0,
) -> CommandResult:
    """Set the editor selection to one or more GameObjects.

    Args:
        bridge: Active bridge connection.
        game_object_paths: List of hierarchy paths to select.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="set-selection",
        parameters={
            "operation": "set",
            "gameObjectPaths": game_object_paths,
        },
        timeout=timeout,
    )


async def clear_selection(
    bridge: DirectBridge,
    timeout: float = 5.0,
) -> CommandResult:
    """Clear the editor selection.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="set-selection",
        parameters={"operation": "clear"},
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrapper
# ---------------------------------------------------------------------------

select_app = typer.Typer(name="select", help="Set or clear Unity Editor selection.")


@select_app.callback(invoke_without_command=True)
def select_cli(
    ctx: typer.Context,
    objects: Annotated[
        list[str] | None,
        typer.Argument(help="GameObject paths to select."),
    ] = None,
    clear: Annotated[
        bool,
        typer.Option("--clear", help="Clear the current selection."),
    ] = False,
) -> None:
    """Select GameObjects or clear the selection."""
    if ctx.invoked_subcommand is not None:
        return
    from unity_bridge.core.output import print_result

    state = ctx.obj

    if clear:
        result = asyncio.run(clear_selection(state.bridge))
    elif objects:
        result = asyncio.run(set_selection(state.bridge, objects))
    else:
        raise typer.BadParameter("Provide OBJECT_PATH(s) or use --clear.")

    print_result(result, state.formatter)

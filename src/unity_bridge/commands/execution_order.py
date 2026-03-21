"""Execution order commands: get and set script execution order."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def get_execution_order(
    bridge: DirectBridge,
    non_default_only: bool = False,
    timeout: float = 15.0,
) -> CommandResult:
    """Get script execution order for all MonoScripts.

    Args:
        bridge: Active bridge connection.
        non_default_only: Only return scripts with non-default (non-zero) order.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {"operation": "get"}
    if non_default_only:
        params["nonDefaultOnly"] = True

    return await bridge.send_command_with_retry(
        command_type="script-execution-order",
        parameters=params,
        timeout=timeout,
    )


async def set_execution_order(
    bridge: DirectBridge,
    script_path: str,
    order: int,
    timeout: float = 15.0,
) -> CommandResult:
    """Set execution order for a specific script.

    Args:
        bridge: Active bridge connection.
        script_path: Asset path to the script (e.g. ``Assets/Scripts/MyScript.cs``).
        order: Execution order value (negative = earlier, positive = later).
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="script-execution-order",
        parameters={
            "operation": "set",
            "scriptPath": script_path,
            "order": order,
        },
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI
# ---------------------------------------------------------------------------

execution_order_app = typer.Typer(
    name="execution-order",
    help="Script execution order management.",
)


@execution_order_app.command("get")
def get_cli(
    ctx: typer.Context,
    non_default: Annotated[
        bool,
        typer.Option("--non-default", help="Only show scripts with non-zero order."),
    ] = False,
) -> None:
    """List all scripts and their execution orders."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(get_execution_order(state.bridge, non_default))
    print_result(result, state.formatter)


@execution_order_app.command("set")
def set_cli(
    ctx: typer.Context,
    script_path: Annotated[str, typer.Argument(help="Asset path to the script.")],
    order: Annotated[int, typer.Argument(help="Execution order value.")],
) -> None:
    """Set execution order for a script."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(set_execution_order(state.bridge, script_path, order))
    print_result(result, state.formatter)

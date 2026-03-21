"""Undo commands: perform, redo, history, clear, group-name, collapse."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Valid actions
# ---------------------------------------------------------------------------

VALID_ACTIONS = frozenset(
    {
        "perform",
        "redo",
        "history",
        "clear",
        "group-name",
        "collapse",
    }
)

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def undo_perform(
    bridge: DirectBridge,
    timeout: float = 5.0,
) -> CommandResult:
    """Undo the last operation.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="undo-operation",
        parameters={"operation": "perform"},
        timeout=timeout,
    )


async def undo_redo(
    bridge: DirectBridge,
    timeout: float = 5.0,
) -> CommandResult:
    """Redo the last undone operation.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="undo-operation",
        parameters={"operation": "redo"},
        timeout=timeout,
    )


async def undo_history(
    bridge: DirectBridge,
    limit: int = 20,
    timeout: float = 5.0,
) -> CommandResult:
    """List recent undo operations (bridge-tracked only).

    Args:
        bridge: Active bridge connection.
        limit: Max history entries to return.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="undo-operation",
        parameters={"operation": "history", "limit": limit},
        timeout=timeout,
    )


async def undo_clear(
    bridge: DirectBridge,
    timeout: float = 5.0,
) -> CommandResult:
    """Clear all undo history.

    WARNING: Clears ALL undo history, including non-bridge operations.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="undo-operation",
        parameters={"operation": "clear"},
        timeout=timeout,
    )


async def undo_group_name(
    bridge: DirectBridge,
    timeout: float = 5.0,
) -> CommandResult:
    """Get the current undo group name.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="undo-operation",
        parameters={"operation": "group-name"},
        timeout=timeout,
    )


async def undo_collapse(
    bridge: DirectBridge,
    group_index: int,
    name: str | None = None,
    timeout: float = 5.0,
) -> CommandResult:
    """Collapse undo operations from a group index into one undo step.

    Args:
        bridge: Active bridge connection.
        group_index: Undo group index to collapse from.
        name: Optional name for the collapsed undo group.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {
        "operation": "collapse",
        "groupIndex": group_index,
    }
    if name is not None:
        params["name"] = name

    return await bridge.send_command_with_retry(
        command_type="undo-operation",
        parameters=params,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrapper
# ---------------------------------------------------------------------------

undo_app = typer.Typer(name="undo", help="Unity Editor undo/redo commands.")


@undo_app.command("perform")
def undo_perform_cli(ctx: typer.Context) -> None:
    """Undo the last operation."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(undo_perform(state.bridge))
    print_result(result, state.formatter)


@undo_app.command("redo")
def undo_redo_cli(ctx: typer.Context) -> None:
    """Redo the last undone operation."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(undo_redo(state.bridge))
    print_result(result, state.formatter)


@undo_app.command("history")
def undo_history_cli(
    ctx: typer.Context,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Max history entries to return."),
    ] = 20,
) -> None:
    """List recent undo operations (bridge-tracked only)."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(undo_history(state.bridge, limit=limit))
    print_result(result, state.formatter)


@undo_app.command("clear")
def undo_clear_cli(ctx: typer.Context) -> None:
    """Clear all undo history (WARNING: affects entire Editor)."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(undo_clear(state.bridge))
    print_result(result, state.formatter)


@undo_app.command("group-name")
def undo_group_name_cli(ctx: typer.Context) -> None:
    """Get the current undo group name."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(undo_group_name(state.bridge))
    print_result(result, state.formatter)


@undo_app.command("collapse")
def undo_collapse_cli(
    ctx: typer.Context,
    group_index: Annotated[
        int,
        typer.Argument(help="Undo group index to collapse from."),
    ],
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Name for the collapsed undo group."),
    ] = None,
) -> None:
    """Collapse operations from a group index into one undo step."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(undo_collapse(state.bridge, group_index, name=name))
    print_result(result, state.formatter)

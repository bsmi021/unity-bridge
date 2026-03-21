"""Lightmap commands: bake, cancel, clear, status, settings."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Valid actions
# ---------------------------------------------------------------------------

VALID_ACTIONS = frozenset({"bake", "cancel", "clear", "status", "settings"})

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def lightmap_bake(
    bridge: DirectBridge,
    run_async: bool = True,
    timeout: float | None = None,
) -> CommandResult:
    """Start a lightmap bake.

    Args:
        bridge: Active bridge connection.
        run_async: If True, return immediately. If False, wait for completion.
        timeout: Timeout in seconds. Defaults to 30 for async, 3600 for sync.
    """
    resolved_timeout = timeout if timeout is not None else (30.0 if run_async else 3600.0)
    return await bridge.send_command_with_retry(
        command_type="lightmap-operation",
        parameters={"operation": "bake", "runAsync": run_async},
        timeout=resolved_timeout,
    )


async def lightmap_cancel(
    bridge: DirectBridge,
    timeout: float = 30.0,
) -> CommandResult:
    """Cancel an in-progress lightmap bake.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="lightmap-operation",
        parameters={"operation": "cancel"},
        timeout=timeout,
    )


async def lightmap_clear(
    bridge: DirectBridge,
    timeout: float = 30.0,
) -> CommandResult:
    """Clear all baked lightmap data from disk.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="lightmap-operation",
        parameters={"operation": "clear"},
        timeout=timeout,
    )


async def lightmap_status(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """Get current lightmap bake status and progress.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds (quick operation).
    """
    return await bridge.send_command_with_retry(
        command_type="lightmap-operation",
        parameters={"operation": "status"},
        timeout=timeout,
    )


async def lightmap_settings(
    bridge: DirectBridge,
    timeout: float = 15.0,
) -> CommandResult:
    """Get current lightmap settings (read-only).

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="lightmap-operation",
        parameters={"operation": "settings"},
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrapper
# ---------------------------------------------------------------------------

lightmap_app = typer.Typer(name="lightmap", help="Lightmap baking commands.")


@lightmap_app.command("bake")
def lightmap_bake_cli(
    ctx: typer.Context,
    run_async: Annotated[
        bool,
        typer.Option("--run-async/--no-run-async", help="Return immediately or wait."),
    ] = True,
    timeout: Annotated[
        float | None,
        typer.Option("--timeout", help="Timeout in seconds."),
    ] = None,
) -> None:
    """Start a lightmap bake."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(lightmap_bake(state.bridge, run_async=run_async, timeout=timeout))
    print_result(result, state.formatter)


@lightmap_app.command("cancel")
def lightmap_cancel_cli(ctx: typer.Context) -> None:
    """Cancel an in-progress lightmap bake."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(lightmap_cancel(state.bridge))
    print_result(result, state.formatter)


@lightmap_app.command("clear")
def lightmap_clear_cli(ctx: typer.Context) -> None:
    """Clear all baked lightmap data."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(lightmap_clear(state.bridge))
    print_result(result, state.formatter)


@lightmap_app.command("status")
def lightmap_status_cli(ctx: typer.Context) -> None:
    """Get current lightmap bake status."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(lightmap_status(state.bridge))
    print_result(result, state.formatter)


@lightmap_app.command("settings")
def lightmap_settings_cli(ctx: typer.Context) -> None:
    """Get current lightmap settings (read-only)."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(lightmap_settings(state.bridge))
    print_result(result, state.formatter)

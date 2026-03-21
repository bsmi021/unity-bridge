"""Assembly reload lock commands: lock, unlock, status."""

from __future__ import annotations

import asyncio

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def assembly_lock(
    bridge: DirectBridge,
    timeout: float = 5.0,
) -> CommandResult:
    """Lock assembly reloading to prevent domain reloads during batch ops.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="assembly-reload-lock",
        parameters={"operation": "lock"},
        timeout=timeout,
    )


async def assembly_unlock(
    bridge: DirectBridge,
    timeout: float = 5.0,
) -> CommandResult:
    """Unlock assembly reloading.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="assembly-reload-lock",
        parameters={"operation": "unlock"},
        timeout=timeout,
    )


async def assembly_lock_status(
    bridge: DirectBridge,
    timeout: float = 5.0,
) -> CommandResult:
    """Check if assembly reloading is currently locked.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="assembly-reload-lock",
        parameters={"operation": "status"},
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI
# ---------------------------------------------------------------------------


def assembly_lock_cli(
    ctx: typer.Context,
) -> None:
    """Lock assembly reloading (prevents domain reload during batch ops)."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(assembly_lock(state.bridge))
    print_result(result, state.formatter)


def assembly_unlock_cli(
    ctx: typer.Context,
) -> None:
    """Unlock assembly reloading."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(assembly_unlock(state.bridge))
    print_result(result, state.formatter)


def assembly_lock_status_cli(
    ctx: typer.Context,
) -> None:
    """Check if assembly reloading is locked."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(assembly_lock_status(state.bridge))
    print_result(result, state.formatter)

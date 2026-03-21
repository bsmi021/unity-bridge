"""Addressables commands: list-groups, build, clean-cache, mark-addressable, set-address."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def addressables_list_groups(
    bridge: DirectBridge,
    timeout: float = 15.0,
) -> CommandResult:
    """List all Addressable groups.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="addressables",
        parameters={"operation": "list-groups"},
        timeout=timeout,
    )


async def addressables_build(
    bridge: DirectBridge,
    timeout: float = 120.0,
) -> CommandResult:
    """Build Addressable content.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="addressables",
        parameters={"operation": "build"},
        timeout=timeout,
    )


async def addressables_clean_cache(
    bridge: DirectBridge,
    timeout: float = 30.0,
) -> CommandResult:
    """Clean Addressable build cache.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="addressables",
        parameters={"operation": "clean-cache"},
        timeout=timeout,
    )


async def addressables_mark(
    bridge: DirectBridge,
    asset_path: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Mark an asset as addressable.

    Args:
        bridge: Active bridge connection.
        asset_path: Asset path to mark.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="addressables",
        parameters={"operation": "mark-addressable", "assetPath": asset_path},
        timeout=timeout,
    )


async def addressables_set_address(
    bridge: DirectBridge,
    asset_path: str,
    address: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Set an asset's addressable address key.

    Args:
        bridge: Active bridge connection.
        asset_path: Asset path of the addressable.
        address: Address key to set.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="addressables",
        parameters={
            "operation": "set-address",
            "assetPath": asset_path,
            "address": address,
        },
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

addressables_app = typer.Typer(name="addressables", help="Addressables commands.")


@addressables_app.command("list-groups")
def addressables_list_cli(ctx: typer.Context) -> None:
    """List all Addressable groups."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(addressables_list_groups(state.bridge))
    print_result(result, state.formatter)


@addressables_app.command("build")
def addressables_build_cli(ctx: typer.Context) -> None:
    """Build Addressable content."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(addressables_build(state.bridge))
    print_result(result, state.formatter)


@addressables_app.command("clean-cache")
def addressables_clean_cli(ctx: typer.Context) -> None:
    """Clean Addressable build cache."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(addressables_clean_cache(state.bridge))
    print_result(result, state.formatter)


@addressables_app.command("mark")
def addressables_mark_cli(
    ctx: typer.Context,
    asset_path: Annotated[str, typer.Argument(help="Asset path to mark.")],
) -> None:
    """Mark an asset as addressable."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(addressables_mark(state.bridge, asset_path))
    print_result(result, state.formatter)


@addressables_app.command("set-address")
def addressables_set_address_cli(
    ctx: typer.Context,
    asset_path: Annotated[str, typer.Argument(help="Asset path.")],
    address: Annotated[str, typer.Argument(help="Address key.")],
) -> None:
    """Set an asset's addressable address key."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(addressables_set_address(state.bridge, asset_path, address))
    print_result(result, state.formatter)

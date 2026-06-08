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


async def addressables_list_profiles(
    bridge: DirectBridge,
    timeout: float = 15.0,
) -> CommandResult:
    """List Addressables profiles."""
    return await bridge.send_command_with_retry(
        command_type="addressables",
        parameters={"operation": "list-profiles"},
        timeout=timeout,
    )


async def addressables_set_active_profile(
    bridge: DirectBridge,
    *,
    profile_id: str | None = None,
    profile_name: str | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Set the active Addressables profile by ID or name."""
    params: dict[str, object] = {"operation": "set-active-profile"}
    if profile_id:
        params["profileId"] = profile_id
    if profile_name:
        params["profileName"] = profile_name
    return await bridge.send_command_with_retry(
        command_type="addressables",
        parameters=params,
        timeout=timeout,
    )


async def addressables_list_labels(
    bridge: DirectBridge,
    timeout: float = 15.0,
) -> CommandResult:
    """List Addressables labels."""
    return await bridge.send_command_with_retry(
        command_type="addressables",
        parameters={"operation": "list-labels"},
        timeout=timeout,
    )


async def addressables_set_label(
    bridge: DirectBridge,
    asset_path: str,
    *,
    label: str,
    enable: bool = True,
    force: bool = False,
    timeout: float = 15.0,
) -> CommandResult:
    """Add or remove an Addressables label on an asset entry."""
    return await bridge.send_command_with_retry(
        command_type="addressables",
        parameters={
            "operation": "set-label",
            "assetPath": asset_path,
            "label": label,
            "enable": enable,
            "force": force,
        },
        timeout=timeout,
    )


async def addressables_list_schemas(
    bridge: DirectBridge,
    timeout: float = 15.0,
) -> CommandResult:
    """List Addressables group schemas."""
    return await bridge.send_command_with_retry(
        command_type="addressables",
        parameters={"operation": "list-schemas"},
        timeout=timeout,
    )


async def addressables_analyze(
    bridge: DirectBridge,
    *,
    analyze_rule: str | None = None,
    output_path: str | None = None,
    timeout: float = 300.0,
) -> CommandResult:
    """Run or inspect Addressables Analyze rules."""
    params: dict[str, object] = {"operation": "analyze"}
    if analyze_rule:
        params["analyzeRule"] = analyze_rule
    if output_path:
        params["outputPath"] = output_path
    return await bridge.send_command_with_retry(
        command_type="addressables",
        parameters=params,
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


@addressables_app.command("profiles")
def addressables_profiles_cli(ctx: typer.Context) -> None:
    """List Addressables profiles."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(addressables_list_profiles(state.bridge))
    print_result(result, state.formatter)


@addressables_app.command("set-profile")
def addressables_set_profile_cli(
    ctx: typer.Context,
    profile_id: Annotated[str | None, typer.Option("--id")] = None,
    profile_name: Annotated[str | None, typer.Option("--name")] = None,
) -> None:
    """Set active Addressables profile."""
    from unity_bridge.core.output import print_result

    if not profile_id and not profile_name:
        raise typer.BadParameter("Provide --id or --name.")

    state = ctx.obj
    result = asyncio.run(
        addressables_set_active_profile(
            state.bridge,
            profile_id=profile_id,
            profile_name=profile_name,
        )
    )
    print_result(result, state.formatter)


@addressables_app.command("labels")
def addressables_labels_cli(ctx: typer.Context) -> None:
    """List Addressables labels."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(addressables_list_labels(state.bridge))
    print_result(result, state.formatter)


@addressables_app.command("set-label")
def addressables_set_label_cli(
    ctx: typer.Context,
    asset_path: Annotated[str, typer.Argument(help="Asset path.")],
    label: Annotated[str, typer.Argument(help="Label name.")],
    enable: Annotated[bool, typer.Option("--enable/--disable")] = True,
    force: Annotated[bool, typer.Option("--force")] = False,
) -> None:
    """Add or remove a label on an addressable entry."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        addressables_set_label(
            state.bridge,
            asset_path,
            label=label,
            enable=enable,
            force=force,
        )
    )
    print_result(result, state.formatter)


@addressables_app.command("schemas")
def addressables_schemas_cli(ctx: typer.Context) -> None:
    """List Addressables group schemas."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(addressables_list_schemas(state.bridge))
    print_result(result, state.formatter)


@addressables_app.command("analyze")
def addressables_analyze_cli(
    ctx: typer.Context,
    rule: Annotated[str | None, typer.Option("--rule")] = None,
    output: Annotated[str | None, typer.Option("--output")] = None,
) -> None:
    """Run or inspect Addressables Analyze rules."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        addressables_analyze(state.bridge, analyze_rule=rule, output_path=output)
    )
    print_result(result, state.formatter)

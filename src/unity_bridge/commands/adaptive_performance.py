"""Unity Adaptive Performance inspection commands."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge


async def adaptive_performance_operation(
    bridge: DirectBridge,
    operation: str,
    *,
    asset_path: str | None = None,
    include_scalers: bool | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Run an Adaptive Performance bridge operation."""
    params: dict[str, object] = {"operation": operation}
    if asset_path:
        params["assetPath"] = asset_path
    if include_scalers is not None:
        params["includeScalers"] = include_scalers
    return await bridge.send_command_with_retry(
        command_type="adaptive-performance",
        parameters=params,
        timeout=timeout,
    )


async def adaptive_performance_availability(
    bridge: DirectBridge,
    timeout: float = 15.0,
) -> CommandResult:
    """Check Adaptive Performance availability."""
    return await adaptive_performance_operation(bridge, "availability", timeout=timeout)


async def adaptive_performance_settings(
    bridge: DirectBridge,
    timeout: float = 15.0,
) -> CommandResult:
    """Read Adaptive Performance project settings."""
    return await adaptive_performance_operation(bridge, "settings", timeout=timeout)


async def adaptive_performance_list_profiles(
    bridge: DirectBridge,
    *,
    include_scalers: bool | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """List Adaptive Performance scaler profiles."""
    return await adaptive_performance_operation(
        bridge,
        "list-profiles",
        include_scalers=include_scalers,
        timeout=timeout,
    )


async def adaptive_performance_inspect_profile(
    bridge: DirectBridge,
    asset_path: str,
    *,
    include_scalers: bool | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Inspect one Adaptive Performance scaler profile."""
    return await adaptive_performance_operation(
        bridge,
        "inspect-profile",
        asset_path=asset_path,
        include_scalers=include_scalers,
        timeout=timeout,
    )


adaptive_performance_app = typer.Typer(
    name="adaptive-performance",
    help="Unity Adaptive Performance inspection.",
)


@adaptive_performance_app.command("availability")
def availability_cli(ctx: typer.Context) -> None:
    """Check Adaptive Performance availability."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(adaptive_performance_availability(state.bridge))
    print_result(result, state.formatter)


@adaptive_performance_app.command("settings")
def settings_cli(ctx: typer.Context) -> None:
    """Read Adaptive Performance project settings."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(adaptive_performance_settings(state.bridge))
    print_result(result, state.formatter)


@adaptive_performance_app.command("list-profiles")
def list_profiles_cli(
    ctx: typer.Context,
    include_scalers: Annotated[bool, typer.Option("--scalers")] = False,
) -> None:
    """List Adaptive Performance scaler profiles."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        adaptive_performance_list_profiles(
            state.bridge,
            include_scalers=include_scalers,
        )
    )
    print_result(result, state.formatter)


@adaptive_performance_app.command("inspect-profile")
def inspect_profile_cli(
    ctx: typer.Context,
    asset_path: Annotated[str, typer.Argument(help="Scaler profile asset path.")],
    include_scalers: Annotated[bool, typer.Option("--scalers")] = True,
) -> None:
    """Inspect one Adaptive Performance scaler profile."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        adaptive_performance_inspect_profile(
            state.bridge,
            asset_path,
            include_scalers=include_scalers,
        )
    )
    print_result(result, state.formatter)

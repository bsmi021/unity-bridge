"""Lightmap commands: bake, cancel, clear, status, settings."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Valid actions
# ---------------------------------------------------------------------------

VALID_ACTIONS = frozenset({"bake", "cancel", "clear", "status", "settings", "set-settings"})

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


async def lightmap_set_settings(
    bridge: DirectBridge,
    baked_gi: bool | None = None,
    realtime_gi: bool | None = None,
    lightmapper: str | None = None,
    bounce_boost: float | None = None,
    indirect_intensity: float | None = None,
    direct_samples: int | None = None,
    indirect_samples: int | None = None,
    lightmap_max_size: int | None = None,
    lightmap_resolution: float | None = None,
    max_bounces: int | None = None,
    compress: bool | None = None,
    ambient_occlusion: bool | None = None,
    ao_max_distance: float | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Set lightmap settings (writable).

    Args:
        bridge: Active bridge connection.
        baked_gi: Enable baked global illumination.
        realtime_gi: Enable realtime global illumination.
        lightmapper: Lightmapper enum (ProgressiveCPU, ProgressiveGPU).
        bounce_boost: Albedo boost (bounce boost).
        indirect_intensity: Indirect light intensity scale.
        direct_samples: Direct sample count.
        indirect_samples: Indirect sample count.
        lightmap_max_size: Maximum lightmap atlas size.
        lightmap_resolution: Lightmap texels per world unit.
        max_bounces: Maximum number of bounces.
        compress: Compress lightmaps.
        ambient_occlusion: Enable ambient occlusion.
        ao_max_distance: AO max distance.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {"operation": "set-settings"}

    if baked_gi is not None:
        params["bakedGI"] = baked_gi
        params["setBakedGI"] = True
    if realtime_gi is not None:
        params["realtimeGI"] = realtime_gi
        params["setRealtimeGI"] = True
    if lightmapper is not None:
        params["lightmapper"] = lightmapper
        params["setLightmapper"] = True
    if bounce_boost is not None:
        params["bounceBoost"] = bounce_boost
        params["setBounceBoost"] = True
    if indirect_intensity is not None:
        params["indirectIntensity"] = indirect_intensity
        params["setIndirectIntensity"] = True
    if direct_samples is not None:
        params["directSampleCount"] = direct_samples
        params["setDirectSampleCount"] = True
    if indirect_samples is not None:
        params["indirectSampleCount"] = indirect_samples
        params["setIndirectSampleCount"] = True
    if lightmap_max_size is not None:
        params["lightmapMaxSize"] = lightmap_max_size
        params["setLightmapMaxSize"] = True
    if lightmap_resolution is not None:
        params["lightmapResolution"] = lightmap_resolution
        params["setLightmapResolution"] = True
    if max_bounces is not None:
        params["maxBounces"] = max_bounces
        params["setMaxBounces"] = True
    if compress is not None:
        params["compressLightmaps"] = compress
        params["setCompressLightmaps"] = True
    if ambient_occlusion is not None:
        params["ambientOcclusion"] = ambient_occlusion
        params["setAmbientOcclusion"] = True
    if ao_max_distance is not None:
        params["aoMaxDistance"] = ao_max_distance
        params["setAoMaxDistance"] = True

    return await bridge.send_command_with_retry(
        command_type="lightmap-operation",
        parameters=params,
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


@lightmap_app.command("set-settings")
def lightmap_set_settings_cli(
    ctx: typer.Context,
    lightmap_size: Annotated[
        int | None,
        typer.Option("--lightmap-size", help="Max lightmap atlas size."),
    ] = None,
    bounces: Annotated[
        int | None,
        typer.Option("--bounces", help="Maximum bounces."),
    ] = None,
    baked_gi: Annotated[
        bool | None,
        typer.Option("--baked-gi/--no-baked-gi", help="Baked GI."),
    ] = None,
    realtime_gi: Annotated[
        bool | None,
        typer.Option("--realtime-gi/--no-realtime-gi", help="Realtime GI."),
    ] = None,
    compress: Annotated[
        bool | None,
        typer.Option("--compress/--no-compress", help="Compress lightmaps."),
    ] = None,
) -> None:
    """Set lightmap settings (writable)."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        lightmap_set_settings(
            state.bridge,
            lightmap_max_size=lightmap_size,
            max_bounces=bounces,
            baked_gi=baked_gi,
            realtime_gi=realtime_gi,
            compress=compress,
        )
    )
    print_result(result, state.formatter)

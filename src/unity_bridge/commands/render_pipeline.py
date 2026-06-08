"""Render pipeline asset inspection and assignment commands."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge


async def render_pipeline_operation(
    bridge: DirectBridge,
    operation: str,
    *,
    asset_path: str | None = None,
    quality_level: str | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Run a render pipeline bridge operation."""
    params: dict[str, object] = {"operation": operation}
    if asset_path:
        params["assetPath"] = asset_path
    if quality_level:
        params["qualityLevel"] = quality_level
    return await bridge.send_command_with_retry(
        command_type="render-pipeline",
        parameters=params,
        timeout=timeout,
    )


async def render_pipeline_list_assets(
    bridge: DirectBridge,
    timeout: float = 15.0,
) -> CommandResult:
    """List RenderPipelineAsset assets."""
    return await render_pipeline_operation(bridge, "list-assets", timeout=timeout)


async def render_pipeline_get_current(
    bridge: DirectBridge,
    timeout: float = 15.0,
) -> CommandResult:
    """Read current/default/quality render pipeline state."""
    return await render_pipeline_operation(bridge, "get-current", timeout=timeout)


async def render_pipeline_set_default(
    bridge: DirectBridge,
    asset_path: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Set the default render pipeline asset."""
    return await render_pipeline_operation(
        bridge,
        "set-default",
        asset_path=asset_path,
        timeout=timeout,
    )


async def render_pipeline_set_quality(
    bridge: DirectBridge,
    asset_path: str,
    *,
    quality_level: str | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Set the active or named quality-level render pipeline override."""
    return await render_pipeline_operation(
        bridge,
        "set-quality",
        asset_path=asset_path,
        quality_level=quality_level,
        timeout=timeout,
    )


async def render_pipeline_inspect(
    bridge: DirectBridge,
    asset_path: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Inspect one RenderPipelineAsset."""
    return await render_pipeline_operation(
        bridge,
        "inspect",
        asset_path=asset_path,
        timeout=timeout,
    )


render_pipeline_app = typer.Typer(name="render-pipeline", help="Render pipeline assets.")


@render_pipeline_app.command("list-assets")
def list_assets_cli(ctx: typer.Context) -> None:
    """List RenderPipelineAsset assets."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    print_result(asyncio.run(render_pipeline_list_assets(state.bridge)), state.formatter)


@render_pipeline_app.command("current")
def current_cli(ctx: typer.Context) -> None:
    """Read current render pipeline state."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    print_result(asyncio.run(render_pipeline_get_current(state.bridge)), state.formatter)


@render_pipeline_app.command("set-default")
def set_default_cli(
    ctx: typer.Context,
    asset_path: Annotated[str, typer.Argument(help="RenderPipelineAsset path or none.")],
) -> None:
    """Set the default render pipeline asset."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    print_result(
        asyncio.run(render_pipeline_set_default(state.bridge, asset_path)),
        state.formatter,
    )


@render_pipeline_app.command("set-quality")
def set_quality_cli(
    ctx: typer.Context,
    asset_path: Annotated[str, typer.Argument(help="RenderPipelineAsset path or none.")],
    quality_level: Annotated[str | None, typer.Option("--quality")] = None,
) -> None:
    """Set the quality render pipeline override."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        render_pipeline_set_quality(
            state.bridge,
            asset_path,
            quality_level=quality_level,
        )
    )
    print_result(result, state.formatter)


@render_pipeline_app.command("inspect")
def inspect_cli(
    ctx: typer.Context,
    asset_path: Annotated[str, typer.Argument(help="RenderPipelineAsset path.")],
) -> None:
    """Inspect one RenderPipelineAsset."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    print_result(
        asyncio.run(render_pipeline_inspect(state.bridge, asset_path)),
        state.formatter,
    )

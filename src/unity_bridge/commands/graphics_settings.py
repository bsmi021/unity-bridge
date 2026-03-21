"""Graphics settings commands: render pipeline, transparency sort, SRP batching."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def graphics_get(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """Get current graphics settings.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="graphics-settings",
        parameters={"operation": "get"},
        timeout=timeout,
    )


async def graphics_set(
    bridge: DirectBridge,
    render_pipeline: str | None = None,
    transparency_sort_mode: str | None = None,
    transparency_sort_axis: tuple[float, float, float] | None = None,
    srp_batching: bool | None = None,
    log_shader_compilation: bool | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Set graphics configuration values.

    Args:
        bridge: Active bridge connection.
        render_pipeline: Asset path to RenderPipelineAsset, or 'none' for built-in.
        transparency_sort_mode: TransparencySortMode enum value.
        transparency_sort_axis: Transparency sort axis as (x, y, z).
        srp_batching: Enable/disable SRP batching.
        log_shader_compilation: Log when shaders are compiled.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {"operation": "set"}

    if render_pipeline is not None:
        params["defaultRenderPipeline"] = render_pipeline
    if transparency_sort_mode is not None:
        params["transparencySortMode"] = transparency_sort_mode
        params["setTransparencySortMode"] = True
    if transparency_sort_axis is not None:
        params["transparencySortAxisX"] = transparency_sort_axis[0]
        params["transparencySortAxisY"] = transparency_sort_axis[1]
        params["transparencySortAxisZ"] = transparency_sort_axis[2]
        params["setTransparencySortAxis"] = True
    if srp_batching is not None:
        params["useScriptableRenderPipelineBatching"] = srp_batching
        params["setSrpBatching"] = True
    if log_shader_compilation is not None:
        params["logWhenShaderIsCompiled"] = log_shader_compilation
        params["setLogShaderCompilation"] = True

    return await bridge.send_command_with_retry(
        command_type="graphics-settings",
        parameters=params,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

graphics_app = typer.Typer(name="graphics", help="Graphics settings commands.")


@graphics_app.command("get")
def graphics_get_cli(ctx: typer.Context) -> None:
    """Get current graphics settings."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(graphics_get(state.bridge))
    print_result(result, state.formatter)


@graphics_app.command("set")
def graphics_set_cli(
    ctx: typer.Context,
    render_pipeline: Annotated[
        str | None,
        typer.Option(
            "--render-pipeline",
            help="Asset path to RenderPipelineAsset, or 'none'.",
        ),
    ] = None,
    srp_batching: Annotated[
        bool | None,
        typer.Option("--srp-batching/--no-srp-batching", help="SRP batching."),
    ] = None,
    log_shader: Annotated[
        bool | None,
        typer.Option(
            "--log-shader/--no-log-shader",
            help="Log shader compilations.",
        ),
    ] = None,
) -> None:
    """Set graphics configuration values."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        graphics_set(
            state.bridge,
            render_pipeline=render_pipeline,
            srp_batching=srp_batching,
            log_shader_compilation=log_shader,
        )
    )
    print_result(result, state.formatter)

"""GraphicsStateCollection tracing and warmup commands."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge


async def graphics_state_operation(
    bridge: DirectBridge,
    operation: str,
    *,
    asset_path: str | None = None,
    output_path: str | None = None,
    progressive_batch_size: int | None = None,
    timeout: float = 300.0,
) -> CommandResult:
    """Run a graphics-state bridge operation."""
    params: dict[str, object] = {"operation": operation}
    if asset_path:
        params["assetPath"] = asset_path
    if output_path:
        params["outputPath"] = output_path
    if progressive_batch_size is not None:
        params["progressiveBatchSize"] = progressive_batch_size
    return await bridge.send_command_with_retry(
        command_type="graphics-state",
        parameters=params,
        timeout=timeout,
    )


async def graphics_state_create(
    bridge: DirectBridge,
    output_path: str,
    timeout: float = 30.0,
) -> CommandResult:
    """Create and save an empty GraphicsStateCollection."""
    return await graphics_state_operation(
        bridge,
        "create",
        output_path=output_path,
        timeout=timeout,
    )


async def graphics_state_load_info(
    bridge: DirectBridge,
    asset_path: str,
    timeout: float = 30.0,
) -> CommandResult:
    """Load and inspect a GraphicsStateCollection file."""
    return await graphics_state_operation(
        bridge,
        "load-info",
        asset_path=asset_path,
        timeout=timeout,
    )


async def graphics_state_begin_trace(
    bridge: DirectBridge,
    timeout: float = 30.0,
) -> CommandResult:
    """Begin tracing graphics states."""
    return await graphics_state_operation(bridge, "begin-trace", timeout=timeout)


async def graphics_state_end_trace_save(
    bridge: DirectBridge,
    output_path: str,
    timeout: float = 30.0,
) -> CommandResult:
    """End tracing and save the active collection."""
    return await graphics_state_operation(
        bridge,
        "end-trace-save",
        output_path=output_path,
        timeout=timeout,
    )


async def graphics_state_warmup(
    bridge: DirectBridge,
    asset_path: str,
    *,
    progressive_batch_size: int | None = None,
    timeout: float = 300.0,
) -> CommandResult:
    """Warm up graphics states from a collection."""
    return await graphics_state_operation(
        bridge,
        "warmup",
        asset_path=asset_path,
        progressive_batch_size=progressive_batch_size,
        timeout=timeout,
    )


async def graphics_state_clear_variants(
    bridge: DirectBridge,
    asset_path: str,
    *,
    output_path: str | None = None,
    timeout: float = 30.0,
) -> CommandResult:
    """Clear variants from a collection and save it."""
    return await graphics_state_operation(
        bridge,
        "clear-variants",
        asset_path=asset_path,
        output_path=output_path,
        timeout=timeout,
    )


graphics_state_app = typer.Typer(
    name="graphics-state",
    help="GraphicsStateCollection trace and warmup.",
)


@graphics_state_app.command("create")
def create_cli(
    ctx: typer.Context,
    output_path: Annotated[str, typer.Argument(help="Output collection path.")],
) -> None:
    """Create an empty GraphicsStateCollection."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    print_result(
        asyncio.run(graphics_state_create(state.bridge, output_path)),
        state.formatter,
    )


@graphics_state_app.command("info")
def info_cli(
    ctx: typer.Context,
    asset_path: Annotated[str, typer.Argument(help="Collection path.")],
) -> None:
    """Inspect a GraphicsStateCollection."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    print_result(
        asyncio.run(graphics_state_load_info(state.bridge, asset_path)),
        state.formatter,
    )


@graphics_state_app.command("begin-trace")
def begin_trace_cli(ctx: typer.Context) -> None:
    """Begin tracing graphics states."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    print_result(asyncio.run(graphics_state_begin_trace(state.bridge)), state.formatter)


@graphics_state_app.command("end-trace-save")
def end_trace_save_cli(
    ctx: typer.Context,
    output_path: Annotated[str, typer.Argument(help="Output collection path.")],
) -> None:
    """End tracing and save the collection."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    print_result(
        asyncio.run(graphics_state_end_trace_save(state.bridge, output_path)),
        state.formatter,
    )


@graphics_state_app.command("warmup")
def warmup_cli(
    ctx: typer.Context,
    asset_path: Annotated[str, typer.Argument(help="Collection path.")],
    progressive_batch_size: Annotated[int | None, typer.Option("--batch-size")] = None,
) -> None:
    """Warm up graphics states."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        graphics_state_warmup(
            state.bridge,
            asset_path,
            progressive_batch_size=progressive_batch_size,
        )
    )
    print_result(result, state.formatter)


@graphics_state_app.command("clear-variants")
def clear_variants_cli(
    ctx: typer.Context,
    asset_path: Annotated[str, typer.Argument(help="Collection path.")],
    output_path: Annotated[str | None, typer.Option("--output")] = None,
) -> None:
    """Clear variants from a collection."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        graphics_state_clear_variants(
            state.bridge,
            asset_path,
            output_path=output_path,
        )
    )
    print_result(result, state.formatter)

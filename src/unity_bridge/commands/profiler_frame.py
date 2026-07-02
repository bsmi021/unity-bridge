"""Per-frame Unity Profiler drill-down commands."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge


async def profiler_frame_operation(
    bridge: DirectBridge,
    operation: str,
    *,
    frame_index: int | None = None,
    frame_index_start: int | None = None,
    frame_index_end: int | None = None,
    marker_name: str | None = None,
    count: int | None = None,
    thread_index: int | None = None,
    depth: int | None = None,
    frame_count: int | None = None,
    log_file: str | None = None,
    timeout: float = 60.0,
) -> CommandResult:
    """Dispatch a profiler-frame operation."""
    params: dict[str, object] = {"operation": operation}
    if frame_index is not None:
        params["frameIndex"] = frame_index
    if frame_index_start is not None:
        params["frameIndexStart"] = frame_index_start
    if frame_index_end is not None:
        params["frameIndexEnd"] = frame_index_end
    if marker_name is not None:
        params["markerName"] = marker_name
    if count is not None:
        params["count"] = count
    if thread_index is not None:
        params["threadIndex"] = thread_index
    if depth is not None:
        params["depth"] = depth
    if frame_count is not None:
        params["frameCount"] = frame_count
    if log_file is not None:
        params["logFile"] = log_file
    return await bridge.send_command_with_retry(
        command_type="profiler-frame",
        parameters=params,
        timeout=timeout,
    )


async def profiler_frame_range(bridge: DirectBridge, timeout: float = 60.0) -> CommandResult:
    return await profiler_frame_operation(bridge, "frame-range", timeout=timeout)


async def profiler_capture_start(
    bridge: DirectBridge,
    *,
    frame_count: int | None = None,
    log_file: str | None = None,
    timeout: float = 60.0,
) -> CommandResult:
    return await profiler_frame_operation(
        bridge,
        "capture-start",
        frame_count=frame_count,
        log_file=log_file,
        timeout=timeout,
    )


async def profiler_capture_stop(
    bridge: DirectBridge,
    timeout: float = 60.0,
) -> CommandResult:
    return await profiler_frame_operation(bridge, "capture-stop", timeout=timeout)


async def profiler_top_time_samples(
    bridge: DirectBridge,
    *,
    frame_index: int,
    count: int = 10,
    thread_index: int = 0,
    timeout: float = 60.0,
) -> CommandResult:
    return await profiler_frame_operation(
        bridge,
        "top-time-samples",
        frame_index=frame_index,
        count=count,
        thread_index=thread_index,
        timeout=timeout,
    )


async def profiler_self_time_samples(
    bridge: DirectBridge,
    *,
    frame_index: int,
    count: int = 10,
    thread_index: int = 0,
    timeout: float = 60.0,
) -> CommandResult:
    return await profiler_frame_operation(
        bridge,
        "self-time-samples",
        frame_index=frame_index,
        count=count,
        thread_index=thread_index,
        timeout=timeout,
    )


async def profiler_sample_time_summary(
    bridge: DirectBridge,
    *,
    marker_name: str,
    frame_index_start: int,
    frame_index_end: int,
    timeout: float = 60.0,
) -> CommandResult:
    return await profiler_frame_operation(
        bridge,
        "sample-time-summary",
        marker_name=marker_name,
        frame_index_start=frame_index_start,
        frame_index_end=frame_index_end,
        timeout=timeout,
    )


async def profiler_bottom_up_tree(
    bridge: DirectBridge,
    *,
    frame_index: int,
    marker_name: str,
    depth: int = 8,
    thread_index: int = 0,
    timeout: float = 60.0,
) -> CommandResult:
    return await profiler_frame_operation(
        bridge,
        "bottom-up-tree",
        frame_index=frame_index,
        marker_name=marker_name,
        depth=depth,
        thread_index=thread_index,
        timeout=timeout,
    )


async def profiler_gc_alloc(
    bridge: DirectBridge,
    *,
    frame_index: int | None = None,
    frame_index_start: int | None = None,
    frame_index_end: int | None = None,
    timeout: float = 60.0,
) -> CommandResult:
    return await profiler_frame_operation(
        bridge,
        "gc-alloc",
        frame_index=frame_index,
        frame_index_start=frame_index_start,
        frame_index_end=frame_index_end,
        timeout=timeout,
    )


async def profiler_sample_gc_alloc(
    bridge: DirectBridge,
    *,
    frame_index: int,
    marker_name: str,
    thread_index: int = 0,
    timeout: float = 60.0,
) -> CommandResult:
    return await profiler_frame_operation(
        bridge,
        "sample-gc-alloc",
        frame_index=frame_index,
        marker_name=marker_name,
        thread_index=thread_index,
        timeout=timeout,
    )


async def profiler_clear(bridge: DirectBridge, timeout: float = 60.0) -> CommandResult:
    return await profiler_frame_operation(bridge, "clear", timeout=timeout)


profiler_frame_app = typer.Typer(name="profiler-frame", help="Profiler frame drill-down.")


@profiler_frame_app.command("capture-start")
def capture_start_cli(
    ctx: typer.Context,
    frame_count: Annotated[
        int | None,
        typer.Option("--frame-count", help="Optional frame budget for the capture."),
    ] = None,
    log_file: Annotated[
        str | None,
        typer.Option("--log-file", help="Optional profiler binary log path."),
    ] = None,
) -> None:
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        profiler_capture_start(state.bridge, frame_count=frame_count, log_file=log_file)
    )
    print_result(result, state.formatter)


@profiler_frame_app.command("capture-stop")
def capture_stop_cli(ctx: typer.Context) -> None:
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(profiler_capture_stop(state.bridge))
    print_result(result, state.formatter)


@profiler_frame_app.command("frame-range")
def frame_range_cli(ctx: typer.Context) -> None:
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(profiler_frame_range(state.bridge))
    print_result(result, state.formatter)


@profiler_frame_app.command("top-time-samples")
def top_time_cli(
    ctx: typer.Context,
    frame_index: Annotated[int, typer.Argument(help="Profiler frame index.")],
    count: Annotated[int, typer.Option("--count", "-c", help="Sample count.")] = 10,
    thread_index: Annotated[int, typer.Option("--thread-index", help="Thread index.")] = 0,
) -> None:
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        profiler_top_time_samples(
            state.bridge,
            frame_index=frame_index,
            count=count,
            thread_index=thread_index,
        )
    )
    print_result(result, state.formatter)


@profiler_frame_app.command("self-time-samples")
def self_time_cli(
    ctx: typer.Context,
    frame_index: Annotated[int, typer.Argument(help="Profiler frame index.")],
    count: Annotated[int, typer.Option("--count", "-c", help="Sample count.")] = 10,
    thread_index: Annotated[int, typer.Option("--thread-index", help="Thread index.")] = 0,
) -> None:
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        profiler_self_time_samples(
            state.bridge,
            frame_index=frame_index,
            count=count,
            thread_index=thread_index,
        )
    )
    print_result(result, state.formatter)


@profiler_frame_app.command("sample-time-summary")
def sample_time_summary_cli(
    ctx: typer.Context,
    marker_name: Annotated[str, typer.Argument(help="Profiler marker name.")],
    start: Annotated[int, typer.Option("--start", help="First frame index.")],
    end: Annotated[int, typer.Option("--end", help="Last frame index.")],
) -> None:
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        profiler_sample_time_summary(
            state.bridge,
            marker_name=marker_name,
            frame_index_start=start,
            frame_index_end=end,
        )
    )
    print_result(result, state.formatter)


@profiler_frame_app.command("bottom-up-tree")
def bottom_up_tree_cli(
    ctx: typer.Context,
    frame_index: Annotated[int, typer.Argument(help="Profiler frame index.")],
    marker_name: Annotated[str, typer.Argument(help="Profiler marker name.")],
    depth: Annotated[int, typer.Option("--depth", help="Maximum ancestor depth.")] = 8,
    thread_index: Annotated[int, typer.Option("--thread-index", help="Thread index.")] = 0,
) -> None:
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        profiler_bottom_up_tree(
            state.bridge,
            frame_index=frame_index,
            marker_name=marker_name,
            depth=depth,
            thread_index=thread_index,
        )
    )
    print_result(result, state.formatter)


@profiler_frame_app.command("gc-alloc")
def gc_alloc_cli(
    ctx: typer.Context,
    frame: Annotated[int | None, typer.Option("--frame", help="Single frame index.")] = None,
    start: Annotated[int | None, typer.Option("--start", help="First frame index.")] = None,
    end: Annotated[int | None, typer.Option("--end", help="Last frame index.")] = None,
) -> None:
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        profiler_gc_alloc(
            state.bridge,
            frame_index=frame,
            frame_index_start=start,
            frame_index_end=end,
        )
    )
    print_result(result, state.formatter)


@profiler_frame_app.command("sample-gc-alloc")
def sample_gc_alloc_cli(
    ctx: typer.Context,
    frame_index: Annotated[int, typer.Argument(help="Profiler frame index.")],
    marker_name: Annotated[str, typer.Argument(help="Profiler marker name.")],
    thread_index: Annotated[int, typer.Option("--thread-index", help="Thread index.")] = 0,
) -> None:
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        profiler_sample_gc_alloc(
            state.bridge,
            frame_index=frame_index,
            marker_name=marker_name,
            thread_index=thread_index,
        )
    )
    print_result(result, state.formatter)


@profiler_frame_app.command("clear")
def clear_cli(ctx: typer.Context) -> None:
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(profiler_clear(state.bridge))
    print_result(result, state.formatter)

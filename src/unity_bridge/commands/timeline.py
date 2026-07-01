"""Timeline commands: create-track, create-clip, get-clips, delete-clip, get-info, evaluate."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def timeline_create_track(
    bridge: DirectBridge,
    timeline_asset_path: str,
    track_type: str,
    track_name: str | None = None,
    timeout: float = 30.0,
) -> CommandResult:
    """Create a top-level track on a TimelineAsset.

    Parent-track grouping is out of scope for v1 — only top-level (null-parent)
    track creation is supported.

    Args:
        bridge: Active bridge connection.
        timeline_asset_path: Asset path to the TimelineAsset.
        track_type: Short track type name (e.g. "AnimationTrack", "AudioTrack").
        track_name: Optional display name for the new track.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {
        "operation": "create-track",
        "timelineAssetPath": timeline_asset_path,
        "trackType": track_type,
    }
    if track_name is not None:
        params["trackName"] = track_name

    return await bridge.send_command_with_retry(
        command_type="timeline-operation",
        parameters=params,
        timeout=timeout,
    )


async def timeline_create_clip(
    bridge: DirectBridge,
    timeline_asset_path: str,
    track_index: int,
    clip_asset_path: str | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Create a clip on a track.

    If clip_asset_path is omitted, a default clip is created via
    TrackAsset.CreateDefaultClip().

    Args:
        bridge: Active bridge connection.
        timeline_asset_path: Asset path to the TimelineAsset.
        track_index: Position of the target track in the timeline's track list.
        clip_asset_path: Optional asset path to a specific PlayableAsset to wrap.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {
        "operation": "create-clip",
        "timelineAssetPath": timeline_asset_path,
        "trackIndex": track_index,
    }
    if clip_asset_path is not None:
        params["clipAssetPath"] = clip_asset_path

    return await bridge.send_command_with_retry(
        command_type="timeline-operation",
        parameters=params,
        timeout=timeout,
    )


async def timeline_get_clips(
    bridge: DirectBridge,
    timeline_asset_path: str,
    track_index: int,
    timeout: float = 10.0,
) -> CommandResult:
    """List clips on a track.

    Returned clipIndex values reflect GetClips() enumeration order at query
    time and can shift after any mutation (delete/create) — re-query before
    reuse.

    Args:
        bridge: Active bridge connection.
        timeline_asset_path: Asset path to the TimelineAsset.
        track_index: Position of the target track in the timeline's track list.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="timeline-operation",
        parameters={
            "operation": "get-clips",
            "timelineAssetPath": timeline_asset_path,
            "trackIndex": track_index,
        },
        timeout=timeout,
    )


async def timeline_delete_clip(
    bridge: DirectBridge,
    timeline_asset_path: str,
    track_index: int,
    clip_index: int,
    timeout: float = 15.0,
) -> CommandResult:
    """Delete a clip from a track by index.

    Args:
        bridge: Active bridge connection.
        timeline_asset_path: Asset path to the TimelineAsset.
        track_index: Position of the target track in the timeline's track list.
        clip_index: Position of the clip in that track's GetClips() order.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="timeline-operation",
        parameters={
            "operation": "delete-clip",
            "timelineAssetPath": timeline_asset_path,
            "trackIndex": track_index,
            "clipIndex": clip_index,
        },
        timeout=timeout,
    )


async def timeline_get_info(
    bridge: DirectBridge,
    timeline_asset_path: str,
    timeout: float = 10.0,
) -> CommandResult:
    """List tracks on a TimelineAsset.

    Args:
        bridge: Active bridge connection.
        timeline_asset_path: Asset path to the TimelineAsset.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="timeline-operation",
        parameters={
            "operation": "get-info",
            "timelineAssetPath": timeline_asset_path,
        },
        timeout=timeout,
    )


async def timeline_evaluate(
    bridge: DirectBridge,
    director_path: str,
    time: float | None = None,
    timeline_asset_path: str | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Evaluate a PlayableDirector, optionally scrubbing to a specific time.

    Args:
        bridge: Active bridge connection.
        director_path: Hierarchy path to the GameObject holding the PlayableDirector.
        time: Optional time in seconds to set before evaluating.
        timeline_asset_path: Optional TimelineAsset path to rebind onto the
            director's playableAsset before evaluating.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {
        "operation": "evaluate",
        "directorPath": director_path,
    }
    if time is not None:
        params["time"] = time
    if timeline_asset_path is not None:
        params["timelineAssetPath"] = timeline_asset_path

    return await bridge.send_command_with_retry(
        command_type="timeline-operation",
        parameters=params,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

timeline_app = typer.Typer(name="timeline", help="Timeline sequencing commands.")


@timeline_app.command("create-track")
def timeline_create_track_cli(
    ctx: typer.Context,
    timeline_asset_path: Annotated[str, typer.Argument(help="Asset path to TimelineAsset.")],
    track_type: Annotated[
        str, typer.Argument(help="Short track type, e.g. AnimationTrack, AudioTrack.")
    ],
    track_name: Annotated[
        str | None, typer.Option("--track-name", help="Display name for the new track.")
    ] = None,
) -> None:
    """Create a top-level track (parent-track grouping is not supported)."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        timeline_create_track(state.bridge, timeline_asset_path, track_type, track_name)
    )
    print_result(result, state.formatter)


@timeline_app.command("create-clip")
def timeline_create_clip_cli(
    ctx: typer.Context,
    timeline_asset_path: Annotated[str, typer.Argument(help="Asset path to TimelineAsset.")],
    track_index: Annotated[int, typer.Argument(help="Target track index.")],
    clip_asset_path: Annotated[
        str | None,
        typer.Option("--clip-asset-path", help="Asset path to a PlayableAsset to wrap."),
    ] = None,
) -> None:
    """Create a clip on a track (default clip if no clip asset given)."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        timeline_create_clip(state.bridge, timeline_asset_path, track_index, clip_asset_path)
    )
    print_result(result, state.formatter)


@timeline_app.command("get-clips")
def timeline_get_clips_cli(
    ctx: typer.Context,
    timeline_asset_path: Annotated[str, typer.Argument(help="Asset path to TimelineAsset.")],
    track_index: Annotated[int, typer.Argument(help="Target track index.")],
) -> None:
    """List clips on a track."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(timeline_get_clips(state.bridge, timeline_asset_path, track_index))
    print_result(result, state.formatter)


@timeline_app.command("delete-clip")
def timeline_delete_clip_cli(
    ctx: typer.Context,
    timeline_asset_path: Annotated[str, typer.Argument(help="Asset path to TimelineAsset.")],
    track_index: Annotated[int, typer.Argument(help="Target track index.")],
    clip_index: Annotated[int, typer.Argument(help="Clip index within the track.")],
) -> None:
    """Delete a clip from a track by index."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        timeline_delete_clip(state.bridge, timeline_asset_path, track_index, clip_index)
    )
    print_result(result, state.formatter)


@timeline_app.command("get-info")
def timeline_get_info_cli(
    ctx: typer.Context,
    timeline_asset_path: Annotated[str, typer.Argument(help="Asset path to TimelineAsset.")],
) -> None:
    """List tracks on a TimelineAsset."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(timeline_get_info(state.bridge, timeline_asset_path))
    print_result(result, state.formatter)


@timeline_app.command("evaluate")
def timeline_evaluate_cli(
    ctx: typer.Context,
    director_path: Annotated[str, typer.Argument(help="Hierarchy path to PlayableDirector.")],
    time: Annotated[
        float | None, typer.Option("--time", help="Time in seconds to scrub to.")
    ] = None,
    timeline_asset_path: Annotated[
        str | None,
        typer.Option("--timeline-asset-path", help="TimelineAsset to rebind before evaluating."),
    ] = None,
) -> None:
    """Evaluate a PlayableDirector, optionally scrubbing to a specific time."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(timeline_evaluate(state.bridge, director_path, time, timeline_asset_path))
    print_result(result, state.formatter)

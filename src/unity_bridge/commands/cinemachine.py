"""Cinemachine commands: camera listing, info, priority, lens, follow/lookat."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def cinemachine_list_cameras(
    bridge: DirectBridge,
    timeout: float = 15.0,
) -> CommandResult:
    """List all Cinemachine cameras in the active scene (including inactive).

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="cinemachine-operation",
        parameters={"operation": "list-cameras"},
        timeout=timeout,
    )


async def cinemachine_get_camera_info(
    bridge: DirectBridge,
    camera_path: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Get priority, lens, follow, and lookat info for one Cinemachine camera.

    Args:
        bridge: Active bridge connection.
        camera_path: Hierarchy path to the CinemachineCamera.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="cinemachine-operation",
        parameters={"operation": "get-camera-info", "cameraPath": camera_path},
        timeout=timeout,
    )


async def cinemachine_set_priority(
    bridge: DirectBridge,
    camera_path: str,
    priority: int,
    timeout: float = 15.0,
) -> CommandResult:
    """Set the priority of a Cinemachine camera.

    Args:
        bridge: Active bridge connection.
        camera_path: Hierarchy path to the CinemachineCamera.
        priority: New priority value.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="cinemachine-operation",
        parameters={
            "operation": "set-priority",
            "cameraPath": camera_path,
            "priority": priority,
        },
        timeout=timeout,
    )


async def cinemachine_set_lens(
    bridge: DirectBridge,
    camera_path: str,
    field_of_view: float | None = None,
    orthographic_size: float | None = None,
    near_clip_plane: float | None = None,
    far_clip_plane: float | None = None,
    dutch: float | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Set any subset of lens fields on a Cinemachine camera.

    Args:
        bridge: Active bridge connection.
        camera_path: Hierarchy path to the CinemachineCamera.
        field_of_view: Vertical field of view in degrees.
        orthographic_size: Orthographic camera half-size.
        near_clip_plane: Near clip plane distance.
        far_clip_plane: Far clip plane distance.
        dutch: Dutch (roll) angle in degrees.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {"operation": "set-lens", "cameraPath": camera_path}
    if field_of_view is not None:
        params["fieldOfView"] = field_of_view
    if orthographic_size is not None:
        params["orthographicSize"] = orthographic_size
    if near_clip_plane is not None:
        params["nearClipPlane"] = near_clip_plane
    if far_clip_plane is not None:
        params["farClipPlane"] = far_clip_plane
    if dutch is not None:
        params["dutch"] = dutch

    return await bridge.send_command_with_retry(
        command_type="cinemachine-operation",
        parameters=params,
        timeout=timeout,
    )


async def cinemachine_set_follow(
    bridge: DirectBridge,
    camera_path: str,
    follow_path: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Set (or clear, with an empty string) the Follow target of a camera.

    Args:
        bridge: Active bridge connection.
        camera_path: Hierarchy path to the CinemachineCamera.
        follow_path: Hierarchy path to the new Follow target, or "" to clear.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="cinemachine-operation",
        parameters={
            "operation": "set-follow",
            "cameraPath": camera_path,
            "followPath": follow_path,
        },
        timeout=timeout,
    )


async def cinemachine_set_lookat(
    bridge: DirectBridge,
    camera_path: str,
    look_at_path: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Set (or clear, with an empty string) the LookAt target of a camera.

    Args:
        bridge: Active bridge connection.
        camera_path: Hierarchy path to the CinemachineCamera.
        look_at_path: Hierarchy path to the new LookAt target, or "" to clear.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="cinemachine-operation",
        parameters={
            "operation": "set-lookat",
            "cameraPath": camera_path,
            "lookAtPath": look_at_path,
        },
        timeout=timeout,
    )


async def cinemachine_get_active_camera(
    bridge: DirectBridge,
    timeout: float = 15.0,
) -> CommandResult:
    """Get the currently active Cinemachine camera via the main camera's brain.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="cinemachine-operation",
        parameters={"operation": "get-active-camera"},
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

cinemachine_app = typer.Typer(name="cinemachine", help="Cinemachine camera commands.")


@cinemachine_app.command("list-cameras")
def cinemachine_list_cameras_cli(ctx: typer.Context) -> None:
    """List all Cinemachine cameras in the active scene."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(cinemachine_list_cameras(state.bridge))
    print_result(result, state.formatter)


@cinemachine_app.command("info")
def cinemachine_get_camera_info_cli(
    ctx: typer.Context,
    camera_path: Annotated[str, typer.Argument(help="Hierarchy path to CinemachineCamera.")],
) -> None:
    """Get priority, lens, follow, and lookat info for one camera."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(cinemachine_get_camera_info(state.bridge, camera_path))
    print_result(result, state.formatter)


@cinemachine_app.command("set-priority")
def cinemachine_set_priority_cli(
    ctx: typer.Context,
    camera_path: Annotated[str, typer.Argument(help="Hierarchy path to CinemachineCamera.")],
    priority: Annotated[int, typer.Argument(help="New priority value.")],
) -> None:
    """Set the priority of a Cinemachine camera."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(cinemachine_set_priority(state.bridge, camera_path, priority))
    print_result(result, state.formatter)


@cinemachine_app.command("set-lens")
def cinemachine_set_lens_cli(
    ctx: typer.Context,
    camera_path: Annotated[str, typer.Argument(help="Hierarchy path to CinemachineCamera.")],
    field_of_view: Annotated[
        float | None,
        typer.Option("--fov", help="Vertical field of view in degrees."),
    ] = None,
    orthographic_size: Annotated[
        float | None,
        typer.Option("--ortho-size", help="Orthographic camera half-size."),
    ] = None,
    near_clip_plane: Annotated[
        float | None,
        typer.Option("--near-clip", help="Near clip plane distance."),
    ] = None,
    far_clip_plane: Annotated[
        float | None,
        typer.Option("--far-clip", help="Far clip plane distance."),
    ] = None,
    dutch: Annotated[
        float | None,
        typer.Option("--dutch", help="Dutch (roll) angle in degrees."),
    ] = None,
) -> None:
    """Set any subset of lens fields on a Cinemachine camera."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        cinemachine_set_lens(
            state.bridge,
            camera_path,
            field_of_view=field_of_view,
            orthographic_size=orthographic_size,
            near_clip_plane=near_clip_plane,
            far_clip_plane=far_clip_plane,
            dutch=dutch,
        )
    )
    print_result(result, state.formatter)


@cinemachine_app.command("set-follow")
def cinemachine_set_follow_cli(
    ctx: typer.Context,
    camera_path: Annotated[str, typer.Argument(help="Hierarchy path to CinemachineCamera.")],
    follow_path: Annotated[
        str,
        typer.Argument(help="Hierarchy path to Follow target ('' to clear)."),
    ] = "",
) -> None:
    """Set or clear the Follow target of a camera."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(cinemachine_set_follow(state.bridge, camera_path, follow_path))
    print_result(result, state.formatter)


@cinemachine_app.command("set-lookat")
def cinemachine_set_lookat_cli(
    ctx: typer.Context,
    camera_path: Annotated[str, typer.Argument(help="Hierarchy path to CinemachineCamera.")],
    look_at_path: Annotated[
        str,
        typer.Argument(help="Hierarchy path to LookAt target ('' to clear)."),
    ] = "",
) -> None:
    """Set or clear the LookAt target of a camera."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(cinemachine_set_lookat(state.bridge, camera_path, look_at_path))
    print_result(result, state.formatter)


@cinemachine_app.command("active")
def cinemachine_get_active_camera_cli(ctx: typer.Context) -> None:
    """Get the currently active Cinemachine camera via the main camera's brain."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(cinemachine_get_active_camera(state.bridge))
    print_result(result, state.formatter)

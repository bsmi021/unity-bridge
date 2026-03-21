"""Animation clip commands: create, info, curves, set-curve, add-event, properties."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def animation_create(
    bridge: DirectBridge,
    clip_path: str,
    frame_rate: float | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Create a new AnimationClip asset.

    Args:
        bridge: Active bridge connection.
        clip_path: Asset path (e.g. 'Assets/Animations/Walk.anim').
        frame_rate: Optional frame rate.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {"operation": "create", "clipPath": clip_path}
    if frame_rate is not None:
        params["frameRate"] = frame_rate
    return await bridge.send_command_with_retry(
        command_type="animation-clip",
        parameters=params,
        timeout=timeout,
    )


async def animation_get_info(
    bridge: DirectBridge,
    clip_path: str,
    timeout: float = 10.0,
) -> CommandResult:
    """Get animation clip info.

    Args:
        bridge: Active bridge connection.
        clip_path: Asset path to the AnimationClip.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="animation-clip",
        parameters={"operation": "get-info", "clipPath": clip_path},
        timeout=timeout,
    )


async def animation_get_curves(
    bridge: DirectBridge,
    clip_path: str,
    timeout: float = 10.0,
) -> CommandResult:
    """List all curve bindings on a clip.

    Args:
        bridge: Active bridge connection.
        clip_path: Asset path to the AnimationClip.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="animation-clip",
        parameters={"operation": "get-curves", "clipPath": clip_path},
        timeout=timeout,
    )


async def animation_set_curve(
    bridge: DirectBridge,
    clip_path: str,
    property_name: str,
    keyframes: list[dict[str, float]],
    relative_path: str = "",
    component_type: str = "Transform",
    timeout: float = 15.0,
) -> CommandResult:
    """Set a curve on an animation clip.

    Args:
        bridge: Active bridge connection.
        clip_path: Asset path to the AnimationClip.
        property_name: Property name to animate.
        keyframes: List of {time, value} dicts.
        relative_path: Relative path to target.
        component_type: Component type name.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="animation-clip",
        parameters={
            "operation": "set-curve",
            "clipPath": clip_path,
            "propertyName": property_name,
            "keyframes": keyframes,
            "relativePath": relative_path,
            "componentType": component_type,
        },
        timeout=timeout,
    )


async def animation_add_event(
    bridge: DirectBridge,
    clip_path: str,
    time: float,
    function_name: str = "OnAnimationEvent",
    string_param: str = "",
    int_param: int = 0,
    float_param: float = 0.0,
    timeout: float = 15.0,
) -> CommandResult:
    """Add an animation event to a clip.

    Args:
        bridge: Active bridge connection.
        clip_path: Asset path to the AnimationClip.
        time: Event time in seconds.
        function_name: Function to call.
        string_param: String parameter.
        int_param: Int parameter.
        float_param: Float parameter.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="animation-clip",
        parameters={
            "operation": "add-event",
            "clipPath": clip_path,
            "eventTime": time,
            "eventFunction": function_name,
            "eventStringParam": string_param,
            "eventIntParam": int_param,
            "eventFloatParam": float_param,
        },
        timeout=timeout,
    )


async def animation_set_properties(
    bridge: DirectBridge,
    clip_path: str,
    looping: bool | None = None,
    wrap_mode: str | None = None,
    frame_rate: float | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Set animation clip properties.

    Args:
        bridge: Active bridge connection.
        clip_path: Asset path to the AnimationClip.
        looping: Whether the clip should loop.
        wrap_mode: WrapMode string.
        frame_rate: Frame rate.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {"operation": "set-properties", "clipPath": clip_path}
    if looping is not None:
        params["looping"] = looping
        params["setLooping"] = True
    if wrap_mode is not None:
        params["wrapMode"] = wrap_mode
    if frame_rate is not None:
        params["frameRate"] = frame_rate

    return await bridge.send_command_with_retry(
        command_type="animation-clip",
        parameters=params,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

animation_app = typer.Typer(name="animation", help="Animation clip commands.")


@animation_app.command("create")
def animation_create_cli(
    ctx: typer.Context,
    clip_path: Annotated[str, typer.Argument(help="Asset path for the new clip.")],
    frame_rate: Annotated[
        float | None,
        typer.Option("--frame-rate", help="Frame rate."),
    ] = None,
) -> None:
    """Create a new AnimationClip asset."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(animation_create(state.bridge, clip_path, frame_rate))
    print_result(result, state.formatter)


@animation_app.command("info")
def animation_info_cli(
    ctx: typer.Context,
    clip_path: Annotated[str, typer.Argument(help="Asset path to the AnimationClip.")],
) -> None:
    """Get animation clip info."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(animation_get_info(state.bridge, clip_path))
    print_result(result, state.formatter)


@animation_app.command("curves")
def animation_curves_cli(
    ctx: typer.Context,
    clip_path: Annotated[str, typer.Argument(help="Asset path to the AnimationClip.")],
) -> None:
    """List all curve bindings on a clip."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(animation_get_curves(state.bridge, clip_path))
    print_result(result, state.formatter)

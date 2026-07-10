"""Editor commands: selection, refresh, focus, menu, screenshot."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions
# ---------------------------------------------------------------------------


async def get_selection(
    bridge: DirectBridge,
    components: bool = False,
    children: bool = False,
    timeout: float = 5.0,
) -> CommandResult:
    """Get the current editor selection.

    Args:
        bridge: Active bridge connection.
        components: Include component lists for selected objects.
        children: Include child objects of each selection.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {}
    if components:
        params["includeComponents"] = True
    if children:
        params["includeChildren"] = True

    return await bridge.send_command_with_retry(
        command_type="get-selection",
        parameters=params,
        timeout=timeout,
    )


async def refresh_assets(
    bridge: DirectBridge,
    force: bool = False,
    timeout: float = 15.0,
) -> CommandResult:
    """Refresh the Unity asset database.

    Args:
        bridge: Active bridge connection.
        force: Force a full refresh even if no changes detected.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {}
    if force:
        params["forceUpdate"] = True

    return await bridge.send_command_with_retry(
        command_type="refresh-assets",
        parameters=params,
        timeout=timeout,
    )


async def focus_object(
    bridge: DirectBridge,
    object_path: str,
    no_frame: bool = False,
    timeout: float = 5.0,
) -> CommandResult:
    """Focus and optionally frame a GameObject in the scene view.

    Args:
        bridge: Active bridge connection.
        object_path: Hierarchy path to the target GameObject.
        no_frame: If True, select but do not frame the object in scene view.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {"gameObjectPath": object_path}
    if no_frame:
        params["frameSelection"] = False

    return await bridge.send_command_with_retry(
        command_type="focus-object",
        parameters=params,
        timeout=timeout,
    )


async def execute_menu_item(
    bridge: DirectBridge,
    menu_path: str,
    validate_only: bool = False,
    timeout: float = 30.0,
) -> CommandResult:
    """Execute or validate a Unity Editor menu item.

    Args:
        bridge: Active bridge connection.
        menu_path: Full menu path (e.g. ``File/Save``).
        validate_only: If True, check if the menu item exists without executing.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {"menuPath": menu_path}
    if validate_only:
        params["validate"] = True

    return await bridge.send_command_with_retry(
        command_type="execute-menu-item",
        parameters=params,
        timeout=timeout,
    )


async def capture_screenshot(
    bridge: DirectBridge,
    output_path: str,
    camera: str | None = None,
    width: int | None = None,
    height: int | None = None,
    return_base64: bool = False,
    multi_angle: bool = False,
    timeout: float = 30.0,
) -> CommandResult:
    """Capture a screenshot from the Unity Editor.

    Args:
        bridge: Active bridge connection.
        output_path: File path to save the screenshot.
        camera: Name of the camera to capture from.
        width: Output width in pixels.
        height: Output height in pixels.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {"outputPath": output_path}
    if camera is not None:
        params["cameraPath"] = camera
    if width is not None:
        params["width"] = width
    if height is not None:
        params["height"] = height
    if return_base64:
        params["returnBase64"] = True
    if multi_angle:
        params["multiAngle"] = True

    return await bridge.send_command_with_retry(
        command_type="capture-screenshot",
        parameters=params,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

editor_app = typer.Typer(name="editor", help="Editor utility commands.")


@editor_app.command("selection")
def selection_cli(
    ctx: typer.Context,
    components: Annotated[
        bool,
        typer.Option("--components", help="Include component lists."),
    ] = False,
    children: Annotated[
        bool,
        typer.Option("--children", help="Include child objects."),
    ] = False,
) -> None:
    """Get the current editor selection."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(get_selection(state.bridge, components, children))
    print_result(result, state.formatter)


@editor_app.command("refresh")
def refresh_cli(
    ctx: typer.Context,
    force: Annotated[
        bool,
        typer.Option("--force", help="Force a full asset refresh."),
    ] = False,
) -> None:
    """Refresh the Unity asset database."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(refresh_assets(state.bridge, force))
    print_result(result, state.formatter)


@editor_app.command("focus")
def focus_cli(
    ctx: typer.Context,
    object_path: Annotated[str, typer.Argument(help="Hierarchy path of the GameObject to focus.")],
    no_frame: Annotated[
        bool,
        typer.Option("--no-frame", help="Select without framing in scene view."),
    ] = False,
) -> None:
    """Focus a GameObject in the scene view."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(focus_object(state.bridge, object_path, no_frame))
    print_result(result, state.formatter)


@editor_app.command("menu")
def menu_cli(
    ctx: typer.Context,
    menu_path: Annotated[str, typer.Argument(help="Full menu path (e.g. File/Save).")],
    validate_only: Annotated[
        bool,
        typer.Option("--validate-only", help="Check existence without executing."),
    ] = False,
) -> None:
    """Execute a Unity Editor menu item."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(execute_menu_item(state.bridge, menu_path, validate_only))
    print_result(result, state.formatter)


@editor_app.command("screenshot")
def screenshot_cli(
    ctx: typer.Context,
    output_path: Annotated[str, typer.Argument(help="File path to save the screenshot.")],
    camera: Annotated[
        str | None,
        typer.Option("--camera", help="Camera name to capture from."),
    ] = None,
    width: Annotated[
        int | None,
        typer.Option("--width", help="Output width in pixels."),
    ] = None,
    height: Annotated[
        int | None,
        typer.Option("--height", help="Output height in pixels."),
    ] = None,
    return_base64: Annotated[
        bool,
        typer.Option("--inline-base64", help="Return base64 PNG data."),
    ] = False,
    multi_angle: Annotated[
        bool,
        typer.Option("--multi-angle", help="Capture scene view from standard angles."),
    ] = False,
) -> None:
    """Capture a screenshot from the Unity Editor."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        capture_screenshot(
            state.bridge,
            output_path,
            camera,
            width,
            height,
            return_base64=return_base64,
            multi_angle=multi_angle,
        )
    )
    print_result(result, state.formatter)

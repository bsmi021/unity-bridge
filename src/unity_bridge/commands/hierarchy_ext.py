"""Phase 5 hierarchy extensions: create-primitive, set-active, remove-component, component toggle.

These commands extend the hierarchy and component groups from hierarchy.py.
"""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def create_primitive(
    bridge: DirectBridge,
    primitive_type: str,
    name: str | None = None,
    parent: str | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Create a primitive or common object in the scene.

    Args:
        bridge: Active bridge connection.
        primitive_type: Type keyword (cube, sphere, camera, etc.).
        name: Optional custom name for the created object.
        parent: Optional parent GameObject path.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {
        "operation": "create-primitive",
        "primitiveType": primitive_type,
    }
    if name is not None:
        params["gameObjectName"] = name
    if parent is not None:
        params["parentPath"] = parent

    return await bridge.send_command_with_retry(
        command_type="gameobject-operation",
        parameters=params,
        timeout=timeout,
    )


async def set_active(
    bridge: DirectBridge,
    object_path: str,
    active: bool = True,
    timeout: float = 10.0,
) -> CommandResult:
    """Set active state on a GameObject.

    Args:
        bridge: Active bridge connection.
        object_path: Hierarchy path to the GameObject.
        active: True to activate, False to deactivate.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="gameobject-operation",
        parameters={
            "operation": "set-active",
            "gameObjectPath": object_path,
            "active": active,
        },
        timeout=timeout,
    )


async def remove_component(
    bridge: DirectBridge,
    object_path: str,
    component_type: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Remove a component from a GameObject.

    Args:
        bridge: Active bridge connection.
        object_path: Hierarchy path to the GameObject.
        component_type: Component type name to remove.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="remove-component",
        parameters={
            "gameObjectPath": object_path,
            "componentType": component_type,
        },
        timeout=timeout,
    )


async def component_toggle(
    bridge: DirectBridge,
    object_path: str,
    component_type: str,
    enabled: bool,
    timeout: float = 10.0,
) -> CommandResult:
    """Enable or disable a component on a GameObject.

    Args:
        bridge: Active bridge connection.
        object_path: Hierarchy path to the GameObject.
        component_type: Component type name.
        enabled: True to enable, False to disable.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="component-toggle",
        parameters={
            "gameObjectPath": object_path,
            "componentType": component_type,
            "enabled": enabled,
        },
        timeout=timeout,
    )


async def scene_load_additive(
    bridge: DirectBridge,
    path: str,
    save_current: bool = False,
    timeout: float = 30.0,
) -> CommandResult:
    """Load a scene additively in the Unity Editor.

    Args:
        bridge: Active bridge connection.
        path: Scene asset path.
        save_current: Save the currently open scene before loading.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="scene-operation",
        parameters={
            "operation": "load",
            "scenePath": path,
            "saveCurrentScene": save_current,
            "mode": "additive",
        },
        timeout=timeout,
    )


async def scene_unload(
    bridge: DirectBridge,
    path: str,
    remove: bool = True,
    timeout: float = 30.0,
) -> CommandResult:
    """Unload an additively loaded scene.

    Args:
        bridge: Active bridge connection.
        path: Scene path to unload.
        remove: Remove the scene from the hierarchy.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="scene-operation",
        parameters={
            "operation": "unload",
            "scenePath": path,
            "removeScene": remove,
        },
        timeout=timeout,
    )


async def scene_set_active(
    bridge: DirectBridge,
    path: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Set the active scene when multiple scenes are loaded.

    Args:
        bridge: Active bridge connection.
        path: Scene path to make active.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="scene-operation",
        parameters={
            "operation": "set-active",
            "scenePath": path,
        },
        timeout=timeout,
    )


async def console_log(
    bridge: DirectBridge,
    message: str,
    log_type: str = "log",
    timeout: float = 5.0,
) -> CommandResult:
    """Log a custom message to the Unity Console.

    Args:
        bridge: Active bridge connection.
        message: Message text to log.
        log_type: Log level -- log, warning, or error.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="console-log",
        parameters={
            "message": message,
            "logType": log_type,
        },
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers — hierarchy extensions
# ---------------------------------------------------------------------------

from unity_bridge.commands.hierarchy import hierarchy_app, component_app  # noqa: E402


@hierarchy_app.command("create-primitive")
def create_primitive_cli(
    ctx: typer.Context,
    primitive_type: Annotated[
        str,
        typer.Argument(
            help=(
                "Object type: cube, sphere, capsule, cylinder, plane, quad, "
                "directional-light, point-light, spot-light, area-light, "
                "camera, particle-system"
            ),
        ),
    ],
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Custom name for the object."),
    ] = None,
    parent: Annotated[
        str | None,
        typer.Option("--parent", "-p", help="Parent GameObject path."),
    ] = None,
) -> None:
    """Create a primitive, light, camera, or particle system."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(create_primitive(state.bridge, primitive_type, name, parent))
    print_result(result, state.formatter)


@hierarchy_app.command("set-active")
def set_active_cli(
    ctx: typer.Context,
    object_path: Annotated[str, typer.Argument(help="Hierarchy path to the GameObject.")],
    active: Annotated[
        bool,
        typer.Option("--active/--inactive", help="Activate or deactivate the GameObject."),
    ] = True,
) -> None:
    """Enable or disable (activate/deactivate) a GameObject."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(set_active(state.bridge, object_path, active))
    print_result(result, state.formatter)


# ---------------------------------------------------------------------------
# Typer CLI wrappers — component extensions
# ---------------------------------------------------------------------------


@component_app.command("remove")
def component_remove_cli(
    ctx: typer.Context,
    object_path: Annotated[str, typer.Argument(help="Hierarchy path to the GameObject.")],
    component_type: Annotated[str, typer.Argument(help="Component type name to remove.")],
) -> None:
    """Remove a component from a GameObject."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(remove_component(state.bridge, object_path, component_type))
    print_result(result, state.formatter)


@component_app.command("enable")
def component_enable_cli(
    ctx: typer.Context,
    object_path: Annotated[str, typer.Argument(help="Hierarchy path to the GameObject.")],
    component_type: Annotated[str, typer.Argument(help="Component type name.")],
) -> None:
    """Enable a component on a GameObject."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(component_toggle(state.bridge, object_path, component_type, True))
    print_result(result, state.formatter)


@component_app.command("disable")
def component_disable_cli(
    ctx: typer.Context,
    object_path: Annotated[str, typer.Argument(help="Hierarchy path to the GameObject.")],
    component_type: Annotated[str, typer.Argument(help="Component type name.")],
) -> None:
    """Disable a component on a GameObject."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(component_toggle(state.bridge, object_path, component_type, False))
    print_result(result, state.formatter)


# ---------------------------------------------------------------------------
# Typer CLI wrappers — scene extensions (additive + unload + set-active)
# ---------------------------------------------------------------------------

from unity_bridge.commands.scene import scene_app  # noqa: E402


@scene_app.command("load-additive")
def scene_load_additive_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Scene asset path to load additively.")],
    save_current: Annotated[
        bool,
        typer.Option("--save-current", help="Save current scene before loading."),
    ] = False,
) -> None:
    """Load a scene additively (keeps existing scenes open)."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(scene_load_additive(state.bridge, path, save_current))
    print_result(result, state.formatter)


@scene_app.command("unload")
def scene_unload_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Scene path to unload.")],
    keep: Annotated[
        bool,
        typer.Option("--keep", help="Keep scene in hierarchy (don't remove)."),
    ] = False,
) -> None:
    """Unload an additively loaded scene."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(scene_unload(state.bridge, path, remove=not keep))
    print_result(result, state.formatter)


@scene_app.command("set-active")
def scene_set_active_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Scene path to set as active.")],
) -> None:
    """Set the active scene (for multi-scene editing)."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(scene_set_active(state.bridge, path))
    print_result(result, state.formatter)


# ---------------------------------------------------------------------------
# Typer CLI wrappers — console log
# ---------------------------------------------------------------------------

from unity_bridge.commands.console import console_app  # noqa: E402


@console_app.command("log")
def console_log_cli(
    ctx: typer.Context,
    message: Annotated[str, typer.Argument(help="Message to log.")],
    log_type: Annotated[
        str,
        typer.Option("--type", "-t", help="Log type: log, warning, error."),
    ] = "log",
) -> None:
    """Log a custom message to the Unity Console."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(console_log(state.bridge, message, log_type))
    print_result(result, state.formatter)

"""Scene management commands: load, save, create."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def scene_load(
    bridge: DirectBridge,
    path: str,
    save_current: bool = False,
    additive: bool = False,
    timeout: float = 30.0,
) -> CommandResult:
    """Load a scene in the Unity Editor.

    Args:
        bridge: Active bridge connection.
        path: Scene asset path (e.g. ``Assets/Scenes/Main.unity``).
        save_current: Save the currently open scene before loading.
        additive: Load additively (keeps existing scenes open).
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {
        "operation": "load",
        "scenePath": path,
        "saveCurrent": save_current,
    }
    if additive:
        params["mode"] = "additive"

    return await bridge.send_command_with_retry(
        command_type="scene-operation",
        parameters=params,
        timeout=timeout,
    )


async def scene_save(
    bridge: DirectBridge,
    timeout: float = 30.0,
) -> CommandResult:
    """Save the currently open scene.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="scene-operation",
        parameters={"operation": "save"},
        timeout=timeout,
    )


async def scene_move_object(
    bridge: DirectBridge,
    object_path: str,
    scene_path: str,
    timeout: float = 30.0,
) -> CommandResult:
    """Move a root GameObject to a different loaded scene."""
    return await bridge.send_command_with_retry(
        command_type="scene-operation",
        parameters={
            "operation": "move-object",
            "gameObjectPath": object_path,
            "scenePath": scene_path,
        },
        timeout=timeout,
    )


async def scene_create(
    bridge: DirectBridge,
    path: str,
    timeout: float = 30.0,
) -> CommandResult:
    """Create a new scene at the given path.

    Args:
        bridge: Active bridge connection.
        path: Asset path for the new scene.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="scene-operation",
        parameters={
            "operation": "create",
            "scenePath": path,
        },
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

scene_app = typer.Typer(name="scene", help="Scene management commands.")


@scene_app.command("load")
def scene_load_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Scene asset path to load.")],
    save_current: Annotated[
        bool,
        typer.Option("--save-current", help="Save current scene before loading."),
    ] = False,
    additive: Annotated[
        bool,
        typer.Option("--additive", help="Load additively (keeps existing scenes)."),
    ] = False,
) -> None:
    """Load a scene in the Unity Editor."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(scene_load(state.bridge, path, save_current, additive))
    print_result(result, state.formatter)


@scene_app.command("save")
def scene_save_cli(ctx: typer.Context) -> None:
    """Save the currently open scene."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(scene_save(state.bridge))
    print_result(result, state.formatter)


@scene_app.command("create")
def scene_create_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Asset path for the new scene.")],
) -> None:
    """Create a new scene at the given path."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(scene_create(state.bridge, path))
    print_result(result, state.formatter)


@scene_app.command("move-object")
def scene_move_object_cli(
    ctx: typer.Context,
    object_path: Annotated[
        str, typer.Argument(help="Hierarchy path of root GameObject to move.")
    ],
    scene_path: Annotated[
        str, typer.Argument(help="Target scene path (must be loaded).")
    ],
) -> None:
    """Move a root GameObject to a different loaded scene."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(scene_move_object(state.bridge, object_path, scene_path))
    print_result(result, state.formatter)

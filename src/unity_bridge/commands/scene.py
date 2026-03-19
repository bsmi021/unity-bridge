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
    timeout: float = 30.0,
) -> CommandResult:
    """Load a scene in the Unity Editor.

    Args:
        bridge: Active bridge connection.
        path: Scene asset path (e.g. ``Assets/Scenes/Main.unity``).
        save_current: Save the currently open scene before loading.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="scene-operation",
        parameters={
            "operation": "load",
            "scenePath": path,
            "saveCurrent": save_current,
        },
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
) -> None:
    """Load a scene in the Unity Editor."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(scene_load(state.bridge, path, save_current))
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

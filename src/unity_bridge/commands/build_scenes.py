"""Build Settings scene list commands: list, add, remove, enable, disable."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def scenes_list(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """List all scenes in Build Settings.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="build-scenes",
        parameters={"operation": "list"},
        timeout=timeout,
    )


async def scenes_add(
    bridge: DirectBridge,
    scene_path: str,
    index: int = -1,
    timeout: float = 15.0,
) -> CommandResult:
    """Add a scene to the Build Settings list.

    Args:
        bridge: Active bridge connection.
        scene_path: Scene asset path (e.g. Assets/Scenes/Main.unity).
        index: Insert position (-1 = append).
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {
        "operation": "add",
        "scenePath": scene_path,
    }
    if index >= 0:
        params["index"] = index
    return await bridge.send_command_with_retry(
        command_type="build-scenes",
        parameters=params,
        timeout=timeout,
    )


async def scenes_remove(
    bridge: DirectBridge,
    scene_path: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Remove a scene from the Build Settings list.

    Args:
        bridge: Active bridge connection.
        scene_path: Scene asset path to remove.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="build-scenes",
        parameters={
            "operation": "remove",
            "scenePath": scene_path,
        },
        timeout=timeout,
    )


async def scenes_enable(
    bridge: DirectBridge,
    scene_path: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Enable a scene in the Build Settings list.

    Args:
        bridge: Active bridge connection.
        scene_path: Scene asset path to enable.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="build-scenes",
        parameters={
            "operation": "enable",
            "scenePath": scene_path,
        },
        timeout=timeout,
    )


async def scenes_disable(
    bridge: DirectBridge,
    scene_path: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Disable a scene in the Build Settings list.

    Args:
        bridge: Active bridge connection.
        scene_path: Scene asset path to disable.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="build-scenes",
        parameters={
            "operation": "disable",
            "scenePath": scene_path,
        },
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrapper
# ---------------------------------------------------------------------------

build_scenes_app = typer.Typer(name="build-scenes", help="Manage Build Settings scene list.")


@build_scenes_app.command("list")
def scenes_list_cli(ctx: typer.Context) -> None:
    """List all scenes in Build Settings."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(scenes_list(state.bridge))
    print_result(result, state.formatter)


@build_scenes_app.command("add")
def scenes_add_cli(
    ctx: typer.Context,
    scene_path: Annotated[str, typer.Argument(help="Scene asset path.")],
    index: Annotated[
        int,
        typer.Option("--index", "-i", help="Position to insert at (-1 = append)."),
    ] = -1,
) -> None:
    """Add a scene to the Build Settings list."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(scenes_add(state.bridge, scene_path, index))
    print_result(result, state.formatter)


@build_scenes_app.command("remove")
def scenes_remove_cli(
    ctx: typer.Context,
    scene_path: Annotated[str, typer.Argument(help="Scene asset path to remove.")],
) -> None:
    """Remove a scene from the Build Settings list."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(scenes_remove(state.bridge, scene_path))
    print_result(result, state.formatter)


@build_scenes_app.command("enable")
def scenes_enable_cli(
    ctx: typer.Context,
    scene_path: Annotated[str, typer.Argument(help="Scene asset path to enable.")],
) -> None:
    """Enable a scene in the Build Settings list."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(scenes_enable(state.bridge, scene_path))
    print_result(result, state.formatter)


@build_scenes_app.command("disable")
def scenes_disable_cli(
    ctx: typer.Context,
    scene_path: Annotated[str, typer.Argument(help="Scene asset path to disable.")],
) -> None:
    """Disable a scene in the Build Settings list."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(scenes_disable(state.bridge, scene_path))
    print_result(result, state.formatter)

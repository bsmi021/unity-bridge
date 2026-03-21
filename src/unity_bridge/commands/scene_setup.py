"""Extended scene commands: setup save/restore/list, play-start, cross-refs,
list-loaded, preview-create, preview-close.

Uses the ``scene-setup-operation`` bridge command type (separate from the
existing ``scene-operation`` type handled by scene.py).
"""

from __future__ import annotations

import asyncio
import re
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_VALID_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def _validate_setup_name(name: str) -> None:
    """Raise ValueError if *name* is not a valid setup name."""
    if not _VALID_NAME_RE.match(name):
        raise ValueError(
            f"Invalid setup name '{name}'. "
            "Use alphanumeric characters, hyphens, and underscores only (max 64 chars)."
        )


# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def scene_setup_save(
    bridge: DirectBridge,
    setup_name: str,
    timeout: float = 30.0,
) -> CommandResult:
    """Save the current multi-scene layout.

    Args:
        bridge: Active bridge connection.
        setup_name: Name for the saved setup (alphanumeric, hyphens, underscores).
        timeout: Timeout in seconds.
    """
    _validate_setup_name(setup_name)
    return await bridge.send_command_with_retry(
        command_type="scene-setup-operation",
        parameters={"operation": "save", "setupName": setup_name},
        timeout=timeout,
    )


async def scene_setup_restore(
    bridge: DirectBridge,
    setup_name: str,
    timeout: float = 30.0,
) -> CommandResult:
    """Restore a previously saved multi-scene layout.

    Args:
        bridge: Active bridge connection.
        setup_name: Name of the setup to restore.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="scene-setup-operation",
        parameters={"operation": "restore", "setupName": setup_name},
        timeout=timeout,
    )


async def scene_setup_list(
    bridge: DirectBridge,
    timeout: float = 30.0,
) -> CommandResult:
    """List all saved scene setups.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="scene-setup-operation",
        parameters={"operation": "list"},
        timeout=timeout,
    )


async def scene_play_start(
    bridge: DirectBridge,
    scene_path: str | None = None,
    clear: bool = False,
    timeout: float = 30.0,
) -> CommandResult:
    """Get, set, or clear the play mode start scene.

    Args:
        bridge: Active bridge connection.
        scene_path: Scene path to set as play mode start scene.
        clear: If True, clear the play mode start scene.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {"operation": "play-start"}
    if clear:
        params["clear"] = True
    elif scene_path is not None:
        params["scenePath"] = scene_path
    return await bridge.send_command_with_retry(
        command_type="scene-setup-operation",
        parameters=params,
        timeout=timeout,
    )


async def scene_cross_refs(
    bridge: DirectBridge,
    timeout: float = 30.0,
) -> CommandResult:
    """Detect cross-scene references across all loaded scenes.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="scene-setup-operation",
        parameters={"operation": "cross-refs"},
        timeout=timeout,
    )


async def scene_list_loaded(
    bridge: DirectBridge,
    timeout: float = 30.0,
) -> CommandResult:
    """List all loaded scenes with status (active, loaded, dirty, path).

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="scene-setup-operation",
        parameters={"operation": "list-loaded"},
        timeout=timeout,
    )


async def scene_preview_create(
    bridge: DirectBridge,
    timeout: float = 30.0,
) -> CommandResult:
    """Create an empty preview scene for isolated testing.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="scene-setup-operation",
        parameters={"operation": "preview-create"},
        timeout=timeout,
    )


async def scene_preview_close(
    bridge: DirectBridge,
    handle: int,
    timeout: float = 30.0,
) -> CommandResult:
    """Close a previously created preview scene.

    Args:
        bridge: Active bridge connection.
        handle: Preview scene handle returned by preview-create.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="scene-setup-operation",
        parameters={"operation": "preview-close", "handle": handle},
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

scene_setup_app = typer.Typer(name="scene-ext", help="Extended scene management commands.")

# Sub-app for setup save/restore/list
setup_app = typer.Typer(name="setup", help="Scene setup save/restore/list.")
scene_setup_app.add_typer(setup_app, name="setup")


@setup_app.command("save")
def setup_save_cli(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name for the saved setup.")],
) -> None:
    """Save the current multi-scene layout."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(scene_setup_save(state.bridge, name))
    print_result(result, state.formatter)


@setup_app.command("restore")
def setup_restore_cli(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name of the setup to restore.")],
) -> None:
    """Restore a previously saved multi-scene layout."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(scene_setup_restore(state.bridge, name))
    print_result(result, state.formatter)


@setup_app.command("list")
def setup_list_cli(ctx: typer.Context) -> None:
    """List all saved scene setups."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(scene_setup_list(state.bridge))
    print_result(result, state.formatter)


@scene_setup_app.command("play-start")
def play_start_cli(
    ctx: typer.Context,
    set_scene: Annotated[
        str | None,
        typer.Option("--set", help="Scene path to set as play mode start scene."),
    ] = None,
    clear: Annotated[
        bool,
        typer.Option("--clear", help="Clear the play mode start scene."),
    ] = False,
) -> None:
    """Get, set, or clear the play mode start scene."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(scene_play_start(state.bridge, scene_path=set_scene, clear=clear))
    print_result(result, state.formatter)


@scene_setup_app.command("cross-refs")
def cross_refs_cli(ctx: typer.Context) -> None:
    """Detect cross-scene references across loaded scenes."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(scene_cross_refs(state.bridge))
    print_result(result, state.formatter)


@scene_setup_app.command("list-loaded")
def list_loaded_cli(ctx: typer.Context) -> None:
    """List all loaded scenes with status."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(scene_list_loaded(state.bridge))
    print_result(result, state.formatter)


@scene_setup_app.command("preview-create")
def preview_create_cli(ctx: typer.Context) -> None:
    """Create an empty preview scene for isolated testing."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(scene_preview_create(state.bridge))
    print_result(result, state.formatter)


@scene_setup_app.command("preview-close")
def preview_close_cli(
    ctx: typer.Context,
    handle: Annotated[int, typer.Argument(help="Preview scene handle.")],
) -> None:
    """Close a previously created preview scene."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(scene_preview_close(state.bridge, handle))
    print_result(result, state.formatter)

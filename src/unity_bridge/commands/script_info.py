"""MonoScript inspection commands: info, list, find-component."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def script_info(
    bridge: DirectBridge,
    asset_path: str,
    timeout: float = 10.0,
) -> CommandResult:
    """Get class info from a script asset path.

    Args:
        bridge: Active bridge connection.
        asset_path: Path to the .cs file in the project.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="script-info",
        parameters={"operation": "info", "assetPath": asset_path},
        timeout=timeout,
    )


async def script_list(
    bridge: DirectBridge,
    filter_name: str | None = None,
    max_results: int = 500,
    timeout: float = 15.0,
) -> CommandResult:
    """List all MonoScripts in the project.

    Args:
        bridge: Active bridge connection.
        filter_name: Filter scripts by name (partial match).
        max_results: Maximum number of results.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {"operation": "list", "maxResults": max_results}
    if filter_name is not None:
        params["filter"] = filter_name

    return await bridge.send_command_with_retry(
        command_type="script-info",
        parameters=params,
        timeout=timeout,
    )


async def script_find_component(
    bridge: DirectBridge,
    game_object_path: str,
    component_type: str,
    timeout: float = 10.0,
) -> CommandResult:
    """Find the MonoScript asset for a component on a GameObject.

    Args:
        bridge: Active bridge connection.
        game_object_path: Hierarchy path to the GameObject.
        component_type: Component type name.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="script-info",
        parameters={
            "operation": "find-component",
            "gameObjectPath": game_object_path,
            "componentType": component_type,
        },
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrapper
# ---------------------------------------------------------------------------

script_info_app = typer.Typer(name="script-info", help="MonoScript inspection commands.")


@script_info_app.command("info")
def script_info_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Asset path to the .cs script.")],
) -> None:
    """Get class info from a script asset."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(script_info(state.bridge, path))
    print_result(result, state.formatter)


@script_info_app.command("list")
def script_list_cli(
    ctx: typer.Context,
    filter_name: Annotated[
        str | None,
        typer.Option("--filter", "-f", help="Filter by name (partial match)."),
    ] = None,
    max_results: Annotated[
        int,
        typer.Option("--max", "-m", help="Max results to return."),
    ] = 500,
) -> None:
    """List all MonoScripts in the project."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(script_list(state.bridge, filter_name, max_results))
    print_result(result, state.formatter)


@script_info_app.command("find-component")
def script_find_component_cli(
    ctx: typer.Context,
    object_path: Annotated[str, typer.Argument(help="Hierarchy path to the GameObject.")],
    component_type: Annotated[str, typer.Argument(help="Component type name.")],
) -> None:
    """Find the script asset for a component on a GameObject."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(script_find_component(state.bridge, object_path, component_type))
    print_result(result, state.formatter)

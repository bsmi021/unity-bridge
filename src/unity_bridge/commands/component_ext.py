"""Component extensions: copy, paste, reset."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def component_copy(
    bridge: DirectBridge,
    object_path: str,
    component_type: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Copy component values to an in-memory buffer.

    Args:
        bridge: Active bridge connection.
        object_path: Hierarchy path to the source GameObject.
        component_type: Component type name to copy.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="component-copy",
        parameters={
            "operation": "copy",
            "gameObjectPath": object_path,
            "componentType": component_type,
        },
        timeout=timeout,
    )


async def component_paste(
    bridge: DirectBridge,
    object_path: str,
    component_type: str,
    data_json: str | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Paste copied component values onto a target component.

    Args:
        bridge: Active bridge connection.
        object_path: Hierarchy path to the target GameObject.
        component_type: Component type name to paste onto.
        data_json: Optional JSON data to paste (overrides buffer).
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {
        "operation": "paste",
        "gameObjectPath": object_path,
        "componentType": component_type,
    }
    if data_json is not None:
        params["dataJson"] = data_json

    return await bridge.send_command_with_retry(
        command_type="component-copy",
        parameters=params,
        timeout=timeout,
    )


async def component_reset(
    bridge: DirectBridge,
    object_path: str,
    component_type: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Reset a component to its default values.

    Args:
        bridge: Active bridge connection.
        object_path: Hierarchy path to the GameObject.
        component_type: Component type name to reset.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="component-reset",
        parameters={
            "gameObjectPath": object_path,
            "componentType": component_type,
        },
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers — attach to component_app from hierarchy.py
# ---------------------------------------------------------------------------

from unity_bridge.commands.hierarchy import component_app  # noqa: E402


@component_app.command("copy")
def component_copy_cli(
    ctx: typer.Context,
    object_path: Annotated[str, typer.Argument(help="Hierarchy path to the source GameObject.")],
    component_type: Annotated[str, typer.Argument(help="Component type name to copy.")],
) -> None:
    """Copy component values to buffer."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(component_copy(state.bridge, object_path, component_type))
    print_result(result, state.formatter)


@component_app.command("paste")
def component_paste_cli(
    ctx: typer.Context,
    object_path: Annotated[str, typer.Argument(help="Hierarchy path to the target GameObject.")],
    component_type: Annotated[str, typer.Argument(help="Component type name to paste onto.")],
    data: Annotated[
        str | None,
        typer.Option("--data", help="JSON data to paste (overrides buffer)."),
    ] = None,
) -> None:
    """Paste copied component values onto a target."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(component_paste(state.bridge, object_path, component_type, data))
    print_result(result, state.formatter)


@component_app.command("reset")
def component_reset_cli(
    ctx: typer.Context,
    object_path: Annotated[str, typer.Argument(help="Hierarchy path to the GameObject.")],
    component_type: Annotated[str, typer.Argument(help="Component type name to reset.")],
) -> None:
    """Reset a component to its default values."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(component_reset(state.bridge, object_path, component_type))
    print_result(result, state.formatter)

"""SerializedProperty commands: list, get, set."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def property_list(
    bridge: DirectBridge,
    object_path: str,
    component_type: str,
    timeout: float = 10.0,
) -> CommandResult:
    """List all serialized properties on a component.

    Args:
        bridge: Active bridge connection.
        object_path: Hierarchy path to the GameObject.
        component_type: Component type name.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="serialized-property",
        parameters={
            "operation": "list",
            "gameObjectPath": object_path,
            "componentType": component_type,
        },
        timeout=timeout,
    )


async def property_get(
    bridge: DirectBridge,
    object_path: str,
    component_type: str,
    property_path: str,
    timeout: float = 10.0,
) -> CommandResult:
    """Get a serialized property value by path.

    Args:
        bridge: Active bridge connection.
        object_path: Hierarchy path to the GameObject.
        component_type: Component type name.
        property_path: SerializedProperty path (e.g. 'health', 'stats.maxHp').
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="serialized-property",
        parameters={
            "operation": "get",
            "gameObjectPath": object_path,
            "componentType": component_type,
            "propertyPath": property_path,
        },
        timeout=timeout,
    )


async def property_set(
    bridge: DirectBridge,
    object_path: str,
    component_type: str,
    property_path: str,
    value: str,
    timeout: float = 30.0,
) -> CommandResult:
    """Set a serialized property value by path.

    Args:
        bridge: Active bridge connection.
        object_path: Hierarchy path to the GameObject.
        component_type: Component type name.
        property_path: SerializedProperty path.
        value: JSON value string.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="serialized-property",
        parameters={
            "operation": "set",
            "gameObjectPath": object_path,
            "componentType": component_type,
            "propertyPath": property_path,
            "valueJson": value,
        },
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

property_app = typer.Typer(name="property", help="SerializedProperty access commands.")


@property_app.command("list")
def property_list_cli(
    ctx: typer.Context,
    object_path: Annotated[str, typer.Argument(help="Hierarchy path to the GameObject.")],
    component_type: Annotated[str, typer.Argument(help="Component type name.")],
) -> None:
    """List all serialized properties on a component."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(property_list(state.bridge, object_path, component_type))
    print_result(result, state.formatter)


@property_app.command("get")
def property_get_cli(
    ctx: typer.Context,
    object_path: Annotated[str, typer.Argument(help="Hierarchy path to the GameObject.")],
    component_type: Annotated[str, typer.Argument(help="Component type name.")],
    property_path: Annotated[str, typer.Argument(help="SerializedProperty path.")],
) -> None:
    """Get a serialized property value."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(property_get(state.bridge, object_path, component_type, property_path))
    print_result(result, state.formatter)


@property_app.command("set")
def property_set_cli(
    ctx: typer.Context,
    object_path: Annotated[str, typer.Argument(help="Hierarchy path to the GameObject.")],
    component_type: Annotated[str, typer.Argument(help="Component type name.")],
    property_path: Annotated[str, typer.Argument(help="SerializedProperty path.")],
    value: Annotated[str, typer.Argument(help="JSON value to set.")],
) -> None:
    """Set a serialized property value."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        property_set(state.bridge, object_path, component_type, property_path, value)
    )
    print_result(result, state.formatter)

"""Deep serialization commands using EditorJsonUtility."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def deep_get(
    bridge: DirectBridge,
    game_object_path: str,
    component_type: str,
    pretty_print: bool = True,
    timeout: float = 10.0,
) -> CommandResult:
    """Get full Editor serialization of a component.

    Uses EditorJsonUtility.ToJson which includes private [SerializeField] fields
    and Editor-only data not available through standard JsonUtility.

    Args:
        bridge: Active bridge connection.
        game_object_path: Hierarchy path to the GameObject.
        component_type: Component type name.
        pretty_print: Format the JSON output.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="deep-serialize",
        parameters={
            "operation": "get",
            "gameObjectPath": game_object_path,
            "componentType": component_type,
            "prettyPrint": pretty_print,
        },
        timeout=timeout,
    )


async def deep_set(
    bridge: DirectBridge,
    game_object_path: str,
    component_type: str,
    json_data: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Overwrite a component from JSON using EditorJsonUtility.

    Args:
        bridge: Active bridge connection.
        game_object_path: Hierarchy path to the GameObject.
        component_type: Component type name.
        json_data: JSON data to overwrite the component with.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="deep-serialize",
        parameters={
            "operation": "set",
            "gameObjectPath": game_object_path,
            "componentType": component_type,
            "json": json_data,
        },
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrapper
# ---------------------------------------------------------------------------

deep_serialize_app = typer.Typer(
    name="deep-serialize", help="EditorJsonUtility deep serialization."
)


@deep_serialize_app.command("get")
def deep_get_cli(
    ctx: typer.Context,
    object_path: Annotated[str, typer.Argument(help="Hierarchy path to the GameObject.")],
    component_type: Annotated[str, typer.Argument(help="Component type name.")],
    compact: Annotated[
        bool,
        typer.Option("--compact", help="Output compact JSON (no pretty print)."),
    ] = False,
) -> None:
    """Get full Editor serialization of a component."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        deep_get(state.bridge, object_path, component_type, pretty_print=not compact)
    )
    print_result(result, state.formatter)


@deep_serialize_app.command("set")
def deep_set_cli(
    ctx: typer.Context,
    object_path: Annotated[str, typer.Argument(help="Hierarchy path to the GameObject.")],
    component_type: Annotated[str, typer.Argument(help="Component type name.")],
    json_data: Annotated[str, typer.Argument(help="JSON data to overwrite with.")],
) -> None:
    """Overwrite a component from JSON."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(deep_set(state.bridge, object_path, component_type, json_data))
    print_result(result, state.formatter)

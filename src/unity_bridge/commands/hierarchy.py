"""Hierarchy and component commands.

Covers: hierarchy query, component get/set/add.
"""

from __future__ import annotations

import asyncio
import json
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def query_hierarchy(
    bridge: DirectBridge,
    depth: int = 5,
    include_inactive: bool = False,
    root: str | None = None,
    timeout: float = 10.0,
) -> CommandResult:
    """Query the scene hierarchy tree.

    Args:
        bridge: Active bridge connection.
        depth: Maximum depth to traverse.
        include_inactive: Include inactive GameObjects.
        root: Optional root GameObject path to start from.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {
        "depth": depth,
        "includeInactive": include_inactive,
    }
    if root is not None:
        params["rootPath"] = root

    return await bridge.send_command_with_retry(
        command_type="query-hierarchy",
        parameters=params,
        timeout=timeout,
    )


async def get_component(
    bridge: DirectBridge,
    object_path: str,
    component_type: str,
    fields: str | None = None,
    timeout: float = 10.0,
) -> CommandResult:
    """Get component data from a GameObject.

    Args:
        bridge: Active bridge connection.
        object_path: Hierarchy path to the GameObject.
        component_type: Component type name (e.g. ``Transform``).
        fields: Comma-separated field names to retrieve.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {
        "objectPath": object_path,
        "componentType": component_type,
    }
    if fields is not None:
        params["fields"] = fields

    return await bridge.send_command_with_retry(
        command_type="get-component-data",
        parameters=params,
        timeout=timeout,
    )


async def set_component(
    bridge: DirectBridge,
    object_path: str,
    component_type: str,
    updates: list[str],
    timeout: float = 30.0,
) -> CommandResult:
    """Set component field values on a GameObject.

    Args:
        bridge: Active bridge connection.
        object_path: Hierarchy path to the GameObject.
        component_type: Component type name.
        updates: List of ``FIELD:JSON`` strings (e.g. ``position.x:1.5``).
        timeout: Timeout in seconds.
    """
    properties = _parse_field_updates(updates)
    return await bridge.send_command_with_retry(
        command_type="set-component-data",
        parameters={
            "objectPath": object_path,
            "componentType": component_type,
            "properties": properties,
        },
        timeout=timeout,
    )


async def add_component(
    bridge: DirectBridge,
    object_path: str,
    component_type: str,
    timeout: float = 30.0,
) -> CommandResult:
    """Add a component to a GameObject.

    Args:
        bridge: Active bridge connection.
        object_path: Hierarchy path to the GameObject.
        component_type: Component type to add.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="add-component",
        parameters={
            "objectPath": object_path,
            "componentType": component_type,
        },
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_field_updates(updates: list[str]) -> dict[str, object]:
    """Parse ``FIELD:JSON`` pairs into a dict.

    Each entry is split on the *first* colon. The value is decoded as JSON;
    if decoding fails it is kept as a plain string.
    """
    properties: dict[str, object] = {}
    for entry in updates:
        if ":" not in entry:
            raise typer.BadParameter(
                f"Invalid update format '{entry}'. Expected FIELD:JSON (e.g. position.x:1.5)"
            )
        field, raw_value = entry.split(":", 1)
        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError:
            value = raw_value
        properties[field.strip()] = value
    return properties


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

hierarchy_app = typer.Typer(name="hierarchy", help="Scene hierarchy commands.")


@hierarchy_app.callback(invoke_without_command=True)
def hierarchy_cli(
    ctx: typer.Context,
    depth: Annotated[
        int, typer.Option("--depth", "-d", help="Maximum traversal depth.")
    ] = 5,
    inactive: Annotated[
        bool, typer.Option("--inactive", help="Include inactive GameObjects.")
    ] = False,
    root: Annotated[
        str | None,
        typer.Option("--root", "-r", help="Root GameObject path to query from."),
    ] = None,
) -> None:
    """Query the active scene hierarchy."""
    if ctx.invoked_subcommand is not None:
        return
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        query_hierarchy(state.bridge, depth, inactive, root)
    )
    print_result(result, state.formatter)


# -- Component sub-group ---------------------------------------------------

component_app = typer.Typer(name="component", help="Component inspection and modification.")


@component_app.command("get")
def component_get_cli(
    ctx: typer.Context,
    object_path: Annotated[str, typer.Argument(help="Hierarchy path to the GameObject.")],
    component_type: Annotated[str, typer.Argument(help="Component type name.")],
    fields: Annotated[
        str | None,
        typer.Option("--fields", "-F", help="Comma-separated field names to retrieve."),
    ] = None,
) -> None:
    """Get component data from a GameObject."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        get_component(state.bridge, object_path, component_type, fields)
    )
    print_result(result, state.formatter)


@component_app.command("set")
def component_set_cli(
    ctx: typer.Context,
    object_path: Annotated[str, typer.Argument(help="Hierarchy path to the GameObject.")],
    component_type: Annotated[str, typer.Argument(help="Component type name.")],
    update: Annotated[
        list[str],
        typer.Option("--update", "-u", help="Field update as FIELD:JSON. Repeatable."),
    ] = [],  # noqa: B006 — Typer requires mutable default for list options
) -> None:
    """Set component field values on a GameObject."""
    from unity_bridge.core.output import print_result

    if not update:
        raise typer.BadParameter("At least one --update FIELD:JSON is required.")

    state = ctx.obj
    result = asyncio.run(
        set_component(state.bridge, object_path, component_type, update)
    )
    print_result(result, state.formatter)


@component_app.command("add")
def component_add_cli(
    ctx: typer.Context,
    object_path: Annotated[str, typer.Argument(help="Hierarchy path to the GameObject.")],
    component_type: Annotated[str, typer.Argument(help="Component type to add.")],
) -> None:
    """Add a component to a GameObject."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        add_component(state.bridge, object_path, component_type)
    )
    print_result(result, state.formatter)

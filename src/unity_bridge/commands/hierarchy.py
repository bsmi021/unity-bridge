"""Hierarchy and component commands.

Covers: hierarchy query, component get/set/add, gameobject utilities.
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
        "gameObjectPath": object_path,
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
            "gameObjectPath": object_path,
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
            "gameObjectPath": object_path,
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
    depth: Annotated[int, typer.Option("--depth", "-d", help="Maximum traversal depth.")] = 5,
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
    result = asyncio.run(query_hierarchy(state.bridge, depth, inactive, root))
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
    result = asyncio.run(get_component(state.bridge, object_path, component_type, fields))
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
    result = asyncio.run(set_component(state.bridge, object_path, component_type, update))
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
    result = asyncio.run(add_component(state.bridge, object_path, component_type))
    print_result(result, state.formatter)


# ---------------------------------------------------------------------------
# Phase 4: Duplicate GameObject
# ---------------------------------------------------------------------------


async def duplicate_gameobject(
    bridge: DirectBridge,
    object_path: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Duplicate a GameObject in the scene.

    Args:
        bridge: Active bridge connection.
        object_path: Hierarchy path to the GameObject to duplicate.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="gameobject-utility",
        parameters={
            "operation": "duplicate",
            "gameObjectPath": object_path,
        },
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Phase 2: GameObject utility core async functions
# ---------------------------------------------------------------------------


async def missing_scripts(
    bridge: DirectBridge,
    fix: bool = False,
    timeout: float = 15.0,
) -> CommandResult:
    """Find (and optionally remove) missing MonoBehaviour scripts.

    Args:
        bridge: Active bridge connection.
        fix: If True, remove the missing scripts.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="gameobject-utility",
        parameters={"operation": "missing-scripts", "fix": fix},
        timeout=timeout,
    )


async def static_flags(
    bridge: DirectBridge,
    object_path: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Get static editor flags for a GameObject.

    Args:
        bridge: Active bridge connection.
        object_path: Hierarchy path to the GameObject.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="gameobject-utility",
        parameters={
            "operation": "static-flags",
            "gameObjectPath": object_path,
        },
        timeout=timeout,
    )


async def set_static_flags(
    bridge: DirectBridge,
    object_path: str,
    flags: list[str],
    timeout: float = 15.0,
) -> CommandResult:
    """Set static editor flags on a GameObject.

    Args:
        bridge: Active bridge connection.
        object_path: Hierarchy path to the GameObject.
        flags: List of flag names (e.g. BatchingStatic, NavigationStatic).
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="gameobject-utility",
        parameters={
            "operation": "set-static-flags",
            "gameObjectPath": object_path,
            "flags": flags,
        },
        timeout=timeout,
    )


async def set_layer(
    bridge: DirectBridge,
    object_path: str,
    layer: int,
    recursive: bool = False,
    timeout: float = 15.0,
) -> CommandResult:
    """Set layer on a GameObject.

    Args:
        bridge: Active bridge connection.
        object_path: Hierarchy path to the GameObject.
        layer: Layer index to set.
        recursive: Apply to all children (including inactive).
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="gameobject-utility",
        parameters={
            "operation": "set-layer",
            "gameObjectPath": object_path,
            "layer": layer,
            "recursive": recursive,
        },
        timeout=timeout,
    )


async def set_tag(
    bridge: DirectBridge,
    object_path: str,
    tag: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Set tag on a GameObject.

    Args:
        bridge: Active bridge connection.
        object_path: Hierarchy path to the GameObject.
        tag: Tag name to set.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="gameobject-utility",
        parameters={
            "operation": "set-tag",
            "gameObjectPath": object_path,
            "tag": tag,
        },
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Phase 2: GameObject utility CLI wrappers
# ---------------------------------------------------------------------------


@hierarchy_app.command("duplicate")
def duplicate_cli(
    ctx: typer.Context,
    object_path: Annotated[str, typer.Argument(help="Hierarchy path to the GameObject.")],
) -> None:
    """Duplicate a GameObject in the scene."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(duplicate_gameobject(state.bridge, object_path))
    print_result(result, state.formatter)


@hierarchy_app.command("missing-scripts")
def missing_scripts_cli(
    ctx: typer.Context,
    fix: Annotated[
        bool,
        typer.Option("--fix", help="Remove missing scripts."),
    ] = False,
) -> None:
    """Find (and optionally fix) missing MonoBehaviour scripts."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(missing_scripts(state.bridge, fix=fix))
    print_result(result, state.formatter)


@hierarchy_app.command("static-flags")
def static_flags_cli(
    ctx: typer.Context,
    object_path: Annotated[str, typer.Argument(help="Hierarchy path to the GameObject.")],
) -> None:
    """Get static editor flags for a GameObject."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(static_flags(state.bridge, object_path))
    print_result(result, state.formatter)


@hierarchy_app.command("set-static-flags")
def set_static_flags_cli(
    ctx: typer.Context,
    object_path: Annotated[str, typer.Argument(help="Hierarchy path to the GameObject.")],
    flags: Annotated[
        list[str],
        typer.Argument(help="Static flag names to set."),
    ],
) -> None:
    """Set static editor flags on a GameObject."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(set_static_flags(state.bridge, object_path, flags))
    print_result(result, state.formatter)


@hierarchy_app.command("set-layer")
def set_layer_cli(
    ctx: typer.Context,
    object_path: Annotated[str, typer.Argument(help="Hierarchy path to the GameObject.")],
    layer: Annotated[int, typer.Argument(help="Layer index to set.")],
    recursive: Annotated[
        bool,
        typer.Option("--recursive", "-r", help="Apply to children (including inactive)."),
    ] = False,
) -> None:
    """Set layer on a GameObject."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(set_layer(state.bridge, object_path, layer, recursive))
    print_result(result, state.formatter)


@hierarchy_app.command("set-tag")
def set_tag_cli(
    ctx: typer.Context,
    object_path: Annotated[str, typer.Argument(help="Hierarchy path to the GameObject.")],
    tag: Annotated[str, typer.Argument(help="Tag name to set.")],
) -> None:
    """Set tag on a GameObject."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(set_tag(state.bridge, object_path, tag))
    print_result(result, state.formatter)

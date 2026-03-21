"""Tags and layers management commands."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def list_tags(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """List all project tags.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="tags-layers",
        parameters={"operation": "list-tags"},
        timeout=timeout,
    )


async def add_tag(
    bridge: DirectBridge,
    tag_name: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Add a custom tag.

    Args:
        bridge: Active bridge connection.
        tag_name: Tag name to add.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="tags-layers",
        parameters={"operation": "add-tag", "tagName": tag_name},
        timeout=timeout,
    )


async def list_layers(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """List all layers (0-31).

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="tags-layers",
        parameters={"operation": "list-layers"},
        timeout=timeout,
    )


async def add_layer(
    bridge: DirectBridge,
    layer_name: str,
    index: int | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Add a layer to a user slot.

    Args:
        bridge: Active bridge connection.
        layer_name: Layer name to add.
        index: Specific slot index (8-31), or None for first empty.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {
        "operation": "add-layer",
        "layerName": layer_name,
    }
    if index is not None:
        params["layerIndex"] = index

    return await bridge.send_command_with_retry(
        command_type="tags-layers",
        parameters=params,
        timeout=timeout,
    )


async def list_sorting_layers(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """List all sorting layers.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="tags-layers",
        parameters={"operation": "list-sorting-layers"},
        timeout=timeout,
    )


async def add_sorting_layer(
    bridge: DirectBridge,
    name: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Add a sorting layer.

    Args:
        bridge: Active bridge connection.
        name: Sorting layer name to add.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="tags-layers",
        parameters={"operation": "add-sorting-layer", "sortingLayerName": name},
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

tags_app = typer.Typer(name="tags", help="Tag management commands.")
layers_app = typer.Typer(name="layers", help="Layer management commands.")
sorting_layers_app = typer.Typer(name="sorting-layers", help="Sorting layer commands.")


@tags_app.command("list")
def tags_list_cli(ctx: typer.Context) -> None:
    """List all project tags."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(list_tags(state.bridge))
    print_result(result, state.formatter)


@tags_app.command("add")
def tags_add_cli(
    ctx: typer.Context,
    tag_name: Annotated[str, typer.Argument(help="Tag name to add.")],
) -> None:
    """Add a custom tag."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(add_tag(state.bridge, tag_name))
    print_result(result, state.formatter)


@layers_app.command("list")
def layers_list_cli(ctx: typer.Context) -> None:
    """List all layers."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(list_layers(state.bridge))
    print_result(result, state.formatter)


@layers_app.command("add")
def layers_add_cli(
    ctx: typer.Context,
    layer_name: Annotated[str, typer.Argument(help="Layer name to add.")],
    index: Annotated[
        int | None,
        typer.Option("--index", "-i", help="Specific slot index (8-31)."),
    ] = None,
) -> None:
    """Add a layer to a user slot."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(add_layer(state.bridge, layer_name, index))
    print_result(result, state.formatter)


@sorting_layers_app.command("list")
def sorting_layers_list_cli(ctx: typer.Context) -> None:
    """List all sorting layers."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(list_sorting_layers(state.bridge))
    print_result(result, state.formatter)


@sorting_layers_app.command("add")
def sorting_layers_add_cli(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Sorting layer name.")],
) -> None:
    """Add a sorting layer."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(add_sorting_layer(state.bridge, name))
    print_result(result, state.formatter)

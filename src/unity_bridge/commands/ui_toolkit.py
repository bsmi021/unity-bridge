"""UI Toolkit authoring and inspection commands."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge


async def ui_list_documents(
    bridge: DirectBridge,
    timeout: float = 15.0,
) -> CommandResult:
    """List UIDocument components in loaded scenes."""
    return await bridge.send_command_with_retry(
        command_type="ui-toolkit",
        parameters={"operation": "list-documents"},
        timeout=timeout,
    )


async def ui_inspect_uxml(
    bridge: DirectBridge,
    asset_path: str,
    *,
    max_depth: int | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Inspect a UXML VisualTreeAsset."""
    params: dict[str, object] = {"operation": "inspect-uxml", "assetPath": asset_path}
    if max_depth is not None:
        params["maxDepth"] = max_depth
    return await bridge.send_command_with_retry(
        command_type="ui-toolkit",
        parameters=params,
        timeout=timeout,
    )


async def ui_inspect_uss(
    bridge: DirectBridge,
    asset_path: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Inspect a USS stylesheet asset."""
    return await bridge.send_command_with_retry(
        command_type="ui-toolkit",
        parameters={"operation": "inspect-uss", "assetPath": asset_path},
        timeout=timeout,
    )


async def ui_create_uxml(
    bridge: DirectBridge,
    asset_path: str,
    *,
    overwrite: bool = False,
    timeout: float = 15.0,
) -> CommandResult:
    """Create a minimal UXML asset."""
    return await bridge.send_command_with_retry(
        command_type="ui-toolkit",
        parameters={
            "operation": "create-uxml",
            "assetPath": asset_path,
            "overwrite": overwrite,
        },
        timeout=timeout,
    )


async def ui_create_panel_settings(
    bridge: DirectBridge,
    asset_path: str,
    *,
    overwrite: bool = False,
    timeout: float = 15.0,
) -> CommandResult:
    """Create a PanelSettings asset."""
    return await bridge.send_command_with_retry(
        command_type="ui-toolkit",
        parameters={
            "operation": "create-panel-settings",
            "assetPath": asset_path,
            "overwrite": overwrite,
        },
        timeout=timeout,
    )


async def ui_add_document(
    bridge: DirectBridge,
    game_object_path: str,
    *,
    uxml_path: str | None = None,
    panel_settings_path: str | None = None,
    sorting_order: int | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Add or configure a UIDocument component on a scene GameObject."""
    params: dict[str, object] = {
        "operation": "add-ui-document",
        "gameObjectPath": game_object_path,
    }
    if uxml_path:
        params["uxmlPath"] = uxml_path
    if panel_settings_path:
        params["panelSettingsPath"] = panel_settings_path
    if sorting_order is not None:
        params["sortingOrder"] = sorting_order
    return await bridge.send_command_with_retry(
        command_type="ui-toolkit",
        parameters=params,
        timeout=timeout,
    )


ui_toolkit_app = typer.Typer(name="ui-toolkit", help="UI Toolkit authoring.")


@ui_toolkit_app.command("list-documents")
def list_documents_cli(ctx: typer.Context) -> None:
    """List UIDocument components."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    print_result(asyncio.run(ui_list_documents(state.bridge)), state.formatter)


@ui_toolkit_app.command("inspect-uxml")
def inspect_uxml_cli(
    ctx: typer.Context,
    asset_path: Annotated[str, typer.Argument(help="UXML asset path.")],
    max_depth: Annotated[int | None, typer.Option("--max-depth")] = None,
) -> None:
    """Inspect a UXML visual tree."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(ui_inspect_uxml(state.bridge, asset_path, max_depth=max_depth))
    print_result(result, state.formatter)


@ui_toolkit_app.command("inspect-uss")
def inspect_uss_cli(
    ctx: typer.Context,
    asset_path: Annotated[str, typer.Argument(help="USS asset path.")],
) -> None:
    """Inspect a USS stylesheet."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    print_result(asyncio.run(ui_inspect_uss(state.bridge, asset_path)), state.formatter)


@ui_toolkit_app.command("create-uxml")
def create_uxml_cli(
    ctx: typer.Context,
    asset_path: Annotated[str, typer.Argument(help="UXML asset path.")],
    overwrite: Annotated[bool, typer.Option("--overwrite")] = False,
) -> None:
    """Create a minimal UXML asset."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(ui_create_uxml(state.bridge, asset_path, overwrite=overwrite))
    print_result(result, state.formatter)


@ui_toolkit_app.command("create-panel-settings")
def create_panel_settings_cli(
    ctx: typer.Context,
    asset_path: Annotated[str, typer.Argument(help="PanelSettings asset path.")],
    overwrite: Annotated[bool, typer.Option("--overwrite")] = False,
) -> None:
    """Create a PanelSettings asset."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        ui_create_panel_settings(state.bridge, asset_path, overwrite=overwrite)
    )
    print_result(result, state.formatter)


@ui_toolkit_app.command("add-document")
def add_document_cli(
    ctx: typer.Context,
    game_object_path: Annotated[str, typer.Argument(help="Scene GameObject path.")],
    uxml_path: Annotated[str | None, typer.Option("--uxml")] = None,
    panel_settings_path: Annotated[str | None, typer.Option("--panel-settings")] = None,
    sorting_order: Annotated[int | None, typer.Option("--sorting-order")] = None,
) -> None:
    """Add or configure UIDocument on a GameObject."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        ui_add_document(
            state.bridge,
            game_object_path,
            uxml_path=uxml_path,
            panel_settings_path=panel_settings_path,
            sorting_order=sorting_order,
        )
    )
    print_result(result, state.formatter)

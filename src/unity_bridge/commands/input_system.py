"""Input System configuration commands."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def input_list_actions(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """List all InputActionAssets and their action maps.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="input-system",
        parameters={"operation": "list-actions"},
        timeout=timeout,
    )


async def input_get_action_map(
    bridge: DirectBridge,
    asset_path: str,
    timeout: float = 10.0,
) -> CommandResult:
    """Get details of a specific InputActionAsset.

    Args:
        bridge: Active bridge connection.
        asset_path: Path to the InputActionAsset.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="input-system",
        parameters={"operation": "get-action-map", "assetPath": asset_path},
        timeout=timeout,
    )


async def input_export(
    bridge: DirectBridge,
    asset_path: str,
    output_path: str | None = None,
    timeout: float = 10.0,
) -> CommandResult:
    """Export an InputActionAsset as JSON.

    Args:
        bridge: Active bridge connection.
        asset_path: Path to the InputActionAsset.
        output_path: Optional file path to save JSON to.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {
        "operation": "export",
        "assetPath": asset_path,
    }
    if output_path is not None:
        params["outputPath"] = output_path

    return await bridge.send_command_with_retry(
        command_type="input-system",
        parameters=params,
        timeout=timeout,
    )


async def input_import(
    bridge: DirectBridge,
    asset_path: str,
    json_data: str | None = None,
    input_path: str | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Import JSON into an InputActionAsset.

    Args:
        bridge: Active bridge connection.
        asset_path: Path for the InputActionAsset.
        json_data: Inline JSON data.
        input_path: Path to a JSON file to import from.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {
        "operation": "import",
        "assetPath": asset_path,
    }
    if json_data is not None:
        params["json"] = json_data
    if input_path is not None:
        params["inputPath"] = input_path

    return await bridge.send_command_with_retry(
        command_type="input-system",
        parameters=params,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrapper
# ---------------------------------------------------------------------------

input_system_app = typer.Typer(name="input-system", help="Input System configuration.")


@input_system_app.command("list")
def input_list_cli(ctx: typer.Context) -> None:
    """List all InputActionAssets in the project."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(input_list_actions(state.bridge))
    print_result(result, state.formatter)


@input_system_app.command("get")
def input_get_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Path to InputActionAsset.")],
) -> None:
    """Get details of an InputActionAsset."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(input_get_action_map(state.bridge, path))
    print_result(result, state.formatter)


@input_system_app.command("export")
def input_export_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Path to InputActionAsset.")],
    output: Annotated[
        str | None,
        typer.Option("--output", "-o", help="File path to save JSON to."),
    ] = None,
) -> None:
    """Export an InputActionAsset as JSON."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(input_export(state.bridge, path, output))
    print_result(result, state.formatter)


@input_system_app.command("import")
def input_import_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Path for the InputActionAsset.")],
    input_file: Annotated[
        str | None,
        typer.Option("--from", "-f", help="JSON file to import from."),
    ] = None,
    json_data: Annotated[
        str | None,
        typer.Option("--json", "-j", help="Inline JSON data."),
    ] = None,
) -> None:
    """Import JSON into an InputActionAsset."""
    from unity_bridge.core.output import print_result

    if not input_file and not json_data:
        raise typer.BadParameter("Provide --from FILE or --json DATA.")

    state = ctx.obj
    result = asyncio.run(input_import(state.bridge, path, json_data, input_file))
    print_result(result, state.formatter)

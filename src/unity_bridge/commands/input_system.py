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


async def input_create_asset(
    bridge: DirectBridge,
    asset_path: str,
    *,
    overwrite: bool = False,
    timeout: float = 30.0,
) -> CommandResult:
    """Create a new InputActionAsset."""
    return await bridge.send_command_with_retry(
        command_type="input-system",
        parameters={
            "operation": "create-asset",
            "assetPath": asset_path,
            "overwrite": overwrite,
        },
        timeout=timeout,
    )


async def input_add_action_map(
    bridge: DirectBridge,
    asset_path: str,
    action_map: str,
    *,
    overwrite: bool = False,
    timeout: float = 30.0,
) -> CommandResult:
    """Add an action map to an InputActionAsset."""
    params: dict[str, object] = {
        "operation": "add-action-map",
        "assetPath": asset_path,
        "actionMap": action_map,
    }
    if overwrite:
        params["overwrite"] = True
    return await bridge.send_command_with_retry(
        command_type="input-system",
        parameters=params,
        timeout=timeout,
    )


async def input_add_action(
    bridge: DirectBridge,
    asset_path: str,
    *,
    action_map: str,
    action_name: str,
    action_type: str | None = None,
    binding_path: str | None = None,
    expected_control_type: str | None = None,
    overwrite: bool = False,
    timeout: float = 30.0,
) -> CommandResult:
    """Add an action to an action map."""
    params: dict[str, object] = {
        "operation": "add-action",
        "assetPath": asset_path,
        "actionMap": action_map,
        "actionName": action_name,
    }
    if action_type:
        params["actionType"] = action_type
    if binding_path:
        params["bindingPath"] = binding_path
    if expected_control_type:
        params["expectedControlType"] = expected_control_type
    if overwrite:
        params["overwrite"] = True
    return await bridge.send_command_with_retry(
        command_type="input-system",
        parameters=params,
        timeout=timeout,
    )


async def input_add_binding(
    bridge: DirectBridge,
    asset_path: str,
    *,
    action_map: str,
    action_name: str,
    binding_path: str,
    interactions: str | None = None,
    processors: str | None = None,
    groups: str | None = None,
    timeout: float = 30.0,
) -> CommandResult:
    """Add a binding to an action."""
    params: dict[str, object] = {
        "operation": "add-binding",
        "assetPath": asset_path,
        "actionMap": action_map,
        "actionName": action_name,
        "bindingPath": binding_path,
    }
    if interactions:
        params["interactions"] = interactions
    if processors:
        params["processors"] = processors
    if groups:
        params["groups"] = groups
    return await bridge.send_command_with_retry(
        command_type="input-system",
        parameters=params,
        timeout=timeout,
    )


async def input_add_control_scheme(
    bridge: DirectBridge,
    asset_path: str,
    *,
    control_scheme: str,
    binding_group: str | None = None,
    device_paths: list[str] | None = None,
    overwrite: bool = False,
    timeout: float = 30.0,
) -> CommandResult:
    """Add a control scheme to an InputActionAsset."""
    params: dict[str, object] = {
        "operation": "add-control-scheme",
        "assetPath": asset_path,
        "controlScheme": control_scheme,
    }
    if binding_group:
        params["bindingGroup"] = binding_group
    if device_paths:
        params["devicePaths"] = device_paths
    if overwrite:
        params["overwrite"] = True
    return await bridge.send_command_with_retry(
        command_type="input-system",
        parameters=params,
        timeout=timeout,
    )


async def input_list_control_schemes(
    bridge: DirectBridge,
    asset_path: str,
    timeout: float = 10.0,
) -> CommandResult:
    """List control schemes from an InputActionAsset."""
    return await bridge.send_command_with_retry(
        command_type="input-system",
        parameters={
            "operation": "list-control-schemes",
            "assetPath": asset_path,
        },
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


@input_system_app.command("create")
def input_create_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Path for the InputActionAsset.")],
    overwrite: Annotated[bool, typer.Option("--overwrite")] = False,
) -> None:
    """Create a new InputActionAsset."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(input_create_asset(state.bridge, path, overwrite=overwrite))
    print_result(result, state.formatter)


@input_system_app.command("add-map")
def input_add_map_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Path to InputActionAsset.")],
    action_map: Annotated[str, typer.Argument(help="Action map name.")],
    overwrite: Annotated[bool, typer.Option("--overwrite")] = False,
) -> None:
    """Add an action map."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        input_add_action_map(state.bridge, path, action_map, overwrite=overwrite)
    )
    print_result(result, state.formatter)


@input_system_app.command("add-action")
def input_add_action_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Path to InputActionAsset.")],
    action_map: Annotated[str, typer.Option("--map", help="Action map name.")],
    action_name: Annotated[str, typer.Option("--name", help="Action name.")],
    action_type: Annotated[str | None, typer.Option("--type")] = None,
    binding_path: Annotated[str | None, typer.Option("--binding")] = None,
    expected_control_type: Annotated[str | None, typer.Option("--expected-control")] = None,
    overwrite: Annotated[bool, typer.Option("--overwrite")] = False,
) -> None:
    """Add an action to an action map."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        input_add_action(
            state.bridge,
            path,
            action_map=action_map,
            action_name=action_name,
            action_type=action_type,
            binding_path=binding_path,
            expected_control_type=expected_control_type,
            overwrite=overwrite,
        )
    )
    print_result(result, state.formatter)


@input_system_app.command("add-binding")
def input_add_binding_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Path to InputActionAsset.")],
    action_map: Annotated[str, typer.Option("--map", help="Action map name.")],
    action_name: Annotated[str, typer.Option("--action", help="Action name.")],
    binding_path: Annotated[str, typer.Option("--binding", help="Control path.")],
    groups: Annotated[str | None, typer.Option("--groups")] = None,
    interactions: Annotated[str | None, typer.Option("--interactions")] = None,
    processors: Annotated[str | None, typer.Option("--processors")] = None,
) -> None:
    """Add a binding to an action."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        input_add_binding(
            state.bridge,
            path,
            action_map=action_map,
            action_name=action_name,
            binding_path=binding_path,
            groups=groups,
            interactions=interactions,
            processors=processors,
        )
    )
    print_result(result, state.formatter)


@input_system_app.command("add-control-scheme")
def input_add_control_scheme_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Path to InputActionAsset.")],
    control_scheme: Annotated[str, typer.Option("--name", help="Control scheme name.")],
    binding_group: Annotated[str | None, typer.Option("--binding-group")] = None,
    device: Annotated[
        list[str] | None, typer.Option("--device", help="Required device path.")
    ] = None,
    overwrite: Annotated[bool, typer.Option("--overwrite")] = False,
) -> None:
    """Add a control scheme."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        input_add_control_scheme(
            state.bridge,
            path,
            control_scheme=control_scheme,
            binding_group=binding_group,
            device_paths=device,
            overwrite=overwrite,
        )
    )
    print_result(result, state.formatter)


@input_system_app.command("control-schemes")
def input_list_control_schemes_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Path to InputActionAsset.")],
) -> None:
    """List control schemes."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(input_list_control_schemes(state.bridge, path))
    print_result(result, state.formatter)

"""Graph Toolkit inspection commands."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge


async def graph_toolkit_operation(
    bridge: DirectBridge,
    operation: str,
    *,
    asset_path: str | None = None,
    include_ports: bool | None = None,
    include_variables: bool | None = None,
    include_annotations: bool | None = None,
    max_elements: int | None = None,
    timeout: float = 30.0,
) -> CommandResult:
    """Run a Graph Toolkit bridge operation."""
    params: dict[str, object] = {"operation": operation}
    if asset_path:
        params["assetPath"] = asset_path
    if include_ports is not None:
        params["includePorts"] = include_ports
    if include_variables is not None:
        params["includeVariables"] = include_variables
    if include_annotations is not None:
        params["includeAnnotations"] = include_annotations
    if max_elements is not None:
        params["maxElements"] = max_elements
    return await bridge.send_command_with_retry(
        command_type="graph-toolkit",
        parameters=params,
        timeout=timeout,
    )


async def graph_toolkit_availability(
    bridge: DirectBridge,
    timeout: float = 30.0,
) -> CommandResult:
    """Check Graph Toolkit availability."""
    return await graph_toolkit_operation(bridge, "availability", timeout=timeout)


async def graph_toolkit_list_assets(
    bridge: DirectBridge,
    timeout: float = 30.0,
) -> CommandResult:
    """List Graph Toolkit graph assets."""
    return await graph_toolkit_operation(bridge, "list-assets", timeout=timeout)


async def graph_toolkit_inspect(
    bridge: DirectBridge,
    asset_path: str,
    *,
    include_ports: bool | None = None,
    include_variables: bool | None = None,
    include_annotations: bool | None = None,
    max_elements: int | None = None,
    timeout: float = 30.0,
) -> CommandResult:
    """Inspect one Graph Toolkit graph asset."""
    return await graph_toolkit_operation(
        bridge,
        "inspect",
        asset_path=asset_path,
        include_ports=include_ports,
        include_variables=include_variables,
        include_annotations=include_annotations,
        max_elements=max_elements,
        timeout=timeout,
    )


async def graph_toolkit_export(
    bridge: DirectBridge,
    asset_path: str,
    *,
    include_ports: bool | None = None,
    include_variables: bool | None = None,
    include_annotations: bool | None = None,
    max_elements: int | None = None,
    timeout: float = 30.0,
) -> CommandResult:
    """Export one Graph Toolkit graph asset as a bridge payload."""
    return await graph_toolkit_operation(
        bridge,
        "export",
        asset_path=asset_path,
        include_ports=include_ports,
        include_variables=include_variables,
        include_annotations=include_annotations,
        max_elements=max_elements,
        timeout=timeout,
    )


graph_toolkit_app = typer.Typer(name="graph-toolkit", help="Graph Toolkit inspection.")


@graph_toolkit_app.command("availability")
def availability_cli(ctx: typer.Context) -> None:
    """Check Graph Toolkit availability."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    print_result(asyncio.run(graph_toolkit_availability(state.bridge)), state.formatter)


@graph_toolkit_app.command("list-assets")
def list_assets_cli(ctx: typer.Context) -> None:
    """List Graph Toolkit graph assets."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    print_result(asyncio.run(graph_toolkit_list_assets(state.bridge)), state.formatter)


@graph_toolkit_app.command("inspect")
def inspect_cli(
    ctx: typer.Context,
    asset_path: Annotated[str, typer.Argument(help="Graph asset path.")],
    include_ports: Annotated[bool, typer.Option("--ports")] = False,
    include_variables: Annotated[bool, typer.Option("--variables")] = False,
    include_annotations: Annotated[bool, typer.Option("--annotations")] = False,
    max_elements: Annotated[int | None, typer.Option("--max-elements")] = None,
) -> None:
    """Inspect one Graph Toolkit graph asset."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        graph_toolkit_inspect(
            state.bridge,
            asset_path,
            include_ports=include_ports,
            include_variables=include_variables,
            include_annotations=include_annotations,
            max_elements=max_elements,
        )
    )
    print_result(result, state.formatter)


@graph_toolkit_app.command("export")
def export_cli(
    ctx: typer.Context,
    asset_path: Annotated[str, typer.Argument(help="Graph asset path.")],
    include_ports: Annotated[bool, typer.Option("--ports")] = True,
    include_variables: Annotated[bool, typer.Option("--variables")] = True,
    include_annotations: Annotated[bool, typer.Option("--annotations")] = True,
    max_elements: Annotated[int | None, typer.Option("--max-elements")] = None,
) -> None:
    """Export one Graph Toolkit graph asset."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        graph_toolkit_export(
            state.bridge,
            asset_path,
            include_ports=include_ports,
            include_variables=include_variables,
            include_annotations=include_annotations,
            max_elements=max_elements,
        )
    )
    print_result(result, state.formatter)

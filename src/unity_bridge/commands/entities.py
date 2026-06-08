"""Unity Entities package inspection commands."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge


async def entities_operation(
    bridge: DirectBridge,
    operation: str,
    *,
    world_name: str | None = None,
    include_systems: bool | None = None,
    include_components: bool | None = None,
    namespace_filter: str | None = None,
    max_systems: int | None = None,
    max_archetypes: int | None = None,
    max_components: int | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Run an Entities bridge operation."""
    params: dict[str, object] = {"operation": operation}
    if world_name:
        params["worldName"] = world_name
    if include_systems is not None:
        params["includeSystems"] = include_systems
    if include_components is not None:
        params["includeComponents"] = include_components
    if namespace_filter:
        params["namespaceFilter"] = namespace_filter
    if max_systems is not None:
        params["maxSystems"] = max_systems
    if max_archetypes is not None:
        params["maxArchetypes"] = max_archetypes
    if max_components is not None:
        params["maxComponents"] = max_components
    return await bridge.send_command_with_retry(
        command_type="entities",
        parameters=params,
        timeout=timeout,
    )


async def entities_availability(
    bridge: DirectBridge,
    timeout: float = 15.0,
) -> CommandResult:
    """Check Unity Entities package/API availability."""
    return await entities_operation(bridge, "availability", timeout=timeout)


async def entities_list_worlds(
    bridge: DirectBridge,
    *,
    include_systems: bool | None = None,
    max_systems: int | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """List loaded Entities worlds."""
    return await entities_operation(
        bridge,
        "list-worlds",
        include_systems=include_systems,
        max_systems=max_systems,
        timeout=timeout,
    )


async def entities_world_summary(
    bridge: DirectBridge,
    *,
    world_name: str | None = None,
    include_systems: bool | None = None,
    max_systems: int | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Summarize one Entities world, or the default world when omitted."""
    return await entities_operation(
        bridge,
        "world-summary",
        world_name=world_name,
        include_systems=include_systems,
        max_systems=max_systems,
        timeout=timeout,
    )


async def entities_list_systems(
    bridge: DirectBridge,
    *,
    world_name: str | None = None,
    namespace_filter: str | None = None,
    max_systems: int | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """List systems in an Entities world."""
    return await entities_operation(
        bridge,
        "list-systems",
        world_name=world_name,
        namespace_filter=namespace_filter,
        max_systems=max_systems,
        timeout=timeout,
    )


async def entities_list_archetypes(
    bridge: DirectBridge,
    *,
    world_name: str | None = None,
    include_components: bool | None = None,
    max_archetypes: int | None = None,
    max_components: int | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """List archetypes in an Entities world."""
    return await entities_operation(
        bridge,
        "list-archetypes",
        world_name=world_name,
        include_components=include_components,
        max_archetypes=max_archetypes,
        max_components=max_components,
        timeout=timeout,
    )


entities_app = typer.Typer(name="entities", help="Unity Entities package inspection.")


@entities_app.command("availability")
def availability_cli(ctx: typer.Context) -> None:
    """Check Unity Entities availability."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    print_result(asyncio.run(entities_availability(state.bridge)), state.formatter)


@entities_app.command("list-worlds")
def list_worlds_cli(
    ctx: typer.Context,
    include_systems: Annotated[bool, typer.Option("--systems")] = False,
    max_systems: Annotated[int | None, typer.Option("--max-systems")] = None,
) -> None:
    """List loaded Entities worlds."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        entities_list_worlds(
            state.bridge,
            include_systems=include_systems,
            max_systems=max_systems,
        )
    )
    print_result(result, state.formatter)


@entities_app.command("world-summary")
def world_summary_cli(
    ctx: typer.Context,
    world_name: Annotated[str | None, typer.Option("--world")] = None,
    include_systems: Annotated[bool, typer.Option("--systems")] = False,
    max_systems: Annotated[int | None, typer.Option("--max-systems")] = None,
) -> None:
    """Summarize one Entities world."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        entities_world_summary(
            state.bridge,
            world_name=world_name,
            include_systems=include_systems,
            max_systems=max_systems,
        )
    )
    print_result(result, state.formatter)


@entities_app.command("list-systems")
def list_systems_cli(
    ctx: typer.Context,
    world_name: Annotated[str | None, typer.Option("--world")] = None,
    namespace_filter: Annotated[str | None, typer.Option("--namespace")] = None,
    max_systems: Annotated[int | None, typer.Option("--max-systems")] = None,
) -> None:
    """List systems in an Entities world."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        entities_list_systems(
            state.bridge,
            world_name=world_name,
            namespace_filter=namespace_filter,
            max_systems=max_systems,
        )
    )
    print_result(result, state.formatter)


@entities_app.command("list-archetypes")
def list_archetypes_cli(
    ctx: typer.Context,
    world_name: Annotated[str | None, typer.Option("--world")] = None,
    include_components: Annotated[bool, typer.Option("--components")] = False,
    max_archetypes: Annotated[int | None, typer.Option("--max-archetypes")] = None,
    max_components: Annotated[int | None, typer.Option("--max-components")] = None,
) -> None:
    """List archetypes in an Entities world."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        entities_list_archetypes(
            state.bridge,
            world_name=world_name,
            include_components=include_components,
            max_archetypes=max_archetypes,
            max_components=max_components,
        )
    )
    print_result(result, state.formatter)

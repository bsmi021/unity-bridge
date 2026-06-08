"""Unity object identity lookups.

Exposes a bridge over legacy instance IDs, stable ``GlobalObjectId`` values,
and Unity 6.x ``EntityId`` values when the Editor API provides them.
"""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge


def _target_params(
    *,
    game_object_path: str | None = None,
    asset_path: str | None = None,
    global_object_id: str | None = None,
    instance_id: int | None = None,
    entity_id: str | None = None,
) -> dict[str, object]:
    params: dict[str, object] = {}
    if game_object_path:
        params["gameObjectPath"] = game_object_path
    if asset_path:
        params["assetPath"] = asset_path
    if global_object_id:
        params["globalObjectId"] = global_object_id
    if instance_id is not None:
        params["instanceId"] = instance_id
    if entity_id:
        params["entityId"] = entity_id
    return params


async def get_selection_identities(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """Return identity data for the current Unity Editor selection."""
    return await bridge.send_command_with_retry(
        command_type="object-identity",
        parameters={"operation": "get-selection"},
        timeout=timeout,
    )


async def resolve_identity(
    bridge: DirectBridge,
    *,
    game_object_path: str | None = None,
    asset_path: str | None = None,
    global_object_id: str | None = None,
    instance_id: int | None = None,
    entity_id: str | None = None,
    timeout: float = 10.0,
) -> CommandResult:
    """Resolve a target from any supported identifier and return identity data."""
    params = {
        "operation": "resolve",
        **_target_params(
            game_object_path=game_object_path,
            asset_path=asset_path,
            global_object_id=global_object_id,
            instance_id=instance_id,
            entity_id=entity_id,
        ),
    }
    return await bridge.send_command_with_retry(
        command_type="object-identity",
        parameters=params,
        timeout=timeout,
    )


async def ping_identity(
    bridge: DirectBridge,
    *,
    game_object_path: str | None = None,
    asset_path: str | None = None,
    global_object_id: str | None = None,
    instance_id: int | None = None,
    entity_id: str | None = None,
    timeout: float = 10.0,
) -> CommandResult:
    """Resolve and ping a Unity object in the Editor."""
    params = {
        "operation": "ping",
        **_target_params(
            game_object_path=game_object_path,
            asset_path=asset_path,
            global_object_id=global_object_id,
            instance_id=instance_id,
            entity_id=entity_id,
        ),
    }
    return await bridge.send_command_with_retry(
        command_type="object-identity",
        parameters=params,
        timeout=timeout,
    )


object_identity_app = typer.Typer(
    name="object-identity",
    help="Resolve Unity object identity values.",
)


@object_identity_app.command("selection")
def selection_cli(ctx: typer.Context) -> None:
    """Return identity data for selected objects."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(get_selection_identities(state.bridge))
    print_result(result, state.formatter)


@object_identity_app.command("resolve")
def resolve_cli(
    ctx: typer.Context,
    game_object_path: Annotated[
        str | None, typer.Option("--game-object-path", help="Scene hierarchy path.")
    ] = None,
    asset_path: Annotated[
        str | None, typer.Option("--asset-path", help="Unity asset path.")
    ] = None,
    global_object_id: Annotated[
        str | None, typer.Option("--global-object-id", help="Unity GlobalObjectId.")
    ] = None,
    instance_id: Annotated[
        int | None, typer.Option("--instance-id", help="Legacy Unity instance ID.")
    ] = None,
    entity_id: Annotated[
        str | None, typer.Option("--entity-id", help="Unity 6 EntityId string.")
    ] = None,
) -> None:
    """Resolve a Unity object from any supported identity."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        resolve_identity(
            state.bridge,
            game_object_path=game_object_path,
            asset_path=asset_path,
            global_object_id=global_object_id,
            instance_id=instance_id,
            entity_id=entity_id,
        )
    )
    print_result(result, state.formatter)


@object_identity_app.command("ping")
def ping_cli(
    ctx: typer.Context,
    game_object_path: Annotated[
        str | None, typer.Option("--game-object-path", help="Scene hierarchy path.")
    ] = None,
    asset_path: Annotated[
        str | None, typer.Option("--asset-path", help="Unity asset path.")
    ] = None,
    global_object_id: Annotated[
        str | None, typer.Option("--global-object-id", help="Unity GlobalObjectId.")
    ] = None,
    instance_id: Annotated[
        int | None, typer.Option("--instance-id", help="Legacy Unity instance ID.")
    ] = None,
    entity_id: Annotated[
        str | None, typer.Option("--entity-id", help="Unity 6 EntityId string.")
    ] = None,
) -> None:
    """Resolve and ping a Unity object."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        ping_identity(
            state.bridge,
            game_object_path=game_object_path,
            asset_path=asset_path,
            global_object_id=global_object_id,
            instance_id=instance_id,
            entity_id=entity_id,
        )
    )
    print_result(result, state.formatter)

"""Prefab commands: validate, instantiate, destroy, overrides, status, unpack."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def prefab_validate(
    bridge: DirectBridge,
    path: str,
    timeout: float = 30.0,
) -> CommandResult:
    """Validate a prefab asset.

    Args:
        bridge: Active bridge connection.
        path: Prefab asset path (e.g. ``Assets/Prefabs/Player.prefab``).
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="validate-prefab",
        parameters={"prefabPath": path},
        timeout=timeout,
    )


async def prefab_instantiate(
    bridge: DirectBridge,
    path: str,
    position: tuple[float, float, float] | None = None,
    timeout: float = 30.0,
) -> CommandResult:
    """Instantiate a prefab into the active scene.

    Args:
        bridge: Active bridge connection.
        path: Prefab asset path.
        position: Optional (x, y, z) world position.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {
        "operation": "instantiate",
        "prefabPath": path,
    }
    if position is not None:
        params["position"] = {
            "x": position[0],
            "y": position[1],
            "z": position[2],
            "isSet": True,
        }

    return await bridge.send_command_with_retry(
        command_type="prefab-operation",
        parameters=params,
        timeout=timeout,
    )


async def prefab_destroy(
    bridge: DirectBridge,
    instance_path: str,
    timeout: float = 30.0,
) -> CommandResult:
    """Destroy a prefab instance in the active scene.

    This removes the *instantiated* GameObject identified by its hierarchy
    path — it does **not** delete the prefab asset on disk.

    Args:
        bridge: Active bridge connection.
        instance_path: Hierarchy path of the instance to destroy.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="prefab-operation",
        parameters={
            "operation": "destroy",
            "gameObjectPath": instance_path,
        },
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_position(value: str) -> tuple[float, float, float]:
    """Parse a ``X,Y,Z`` string into a three-float tuple."""
    parts = value.split(",")
    if len(parts) != 3:
        raise typer.BadParameter(
            f"Position must be three comma-separated floats (X,Y,Z), got '{value}'"
        )
    try:
        return (float(parts[0]), float(parts[1]), float(parts[2]))
    except ValueError as exc:
        raise typer.BadParameter(f"Position components must be numbers, got '{value}'") from exc


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

prefab_app = typer.Typer(name="prefab", help="Prefab management commands.")


@prefab_app.command("validate")
def prefab_validate_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Prefab asset path to validate.")],
) -> None:
    """Validate a prefab asset."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(prefab_validate(state.bridge, path))
    print_result(result, state.formatter)


@prefab_app.command("instantiate")
def prefab_instantiate_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Prefab asset path to instantiate.")],
    position: Annotated[
        str | None,
        typer.Option("--position", "-pos", help="World position as X,Y,Z."),
    ] = None,
) -> None:
    """Instantiate a prefab into the active scene."""
    from unity_bridge.core.output import print_result

    parsed_pos = _parse_position(position) if position is not None else None
    state = ctx.obj
    result = asyncio.run(prefab_instantiate(state.bridge, path, parsed_pos))
    print_result(result, state.formatter)


@prefab_app.command("destroy")
def prefab_destroy_cli(
    ctx: typer.Context,
    instance_path: Annotated[
        str,
        typer.Argument(help="Hierarchy path of the prefab instance to destroy."),
    ],
) -> None:
    """Destroy a prefab instance in the active scene."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(prefab_destroy(state.bridge, instance_path))
    print_result(result, state.formatter)


# ---------------------------------------------------------------------------
# Phase 2: Prefab override core async functions
# ---------------------------------------------------------------------------

VALID_OVERRIDE_ACTIONS = frozenset(
    {
        "list",
        "apply",
        "revert",
        "status",
        "find-instances",
        "unpack",
    }
)


async def prefab_overrides_list(
    bridge: DirectBridge,
    instance_path: str,
    include_default_overrides: bool = False,
    timeout: float = 30.0,
) -> CommandResult:
    """List all overrides on a prefab instance.

    Args:
        bridge: Active bridge connection.
        instance_path: Hierarchy path to the prefab instance.
        include_default_overrides: Include default overrides (position/rotation).
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="prefab-override",
        parameters={
            "operation": "list",
            "instancePath": instance_path,
            "includeDefaultOverrides": include_default_overrides,
        },
        timeout=timeout,
    )


async def prefab_overrides_apply(
    bridge: DirectBridge,
    instance_path: str,
    target: str | None = None,
    timeout: float = 30.0,
) -> CommandResult:
    """Apply overrides from a prefab instance to the prefab asset.

    Args:
        bridge: Active bridge connection.
        instance_path: Hierarchy path to the prefab instance.
        target: Specific override to apply (omit for all).
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {
        "operation": "apply",
        "instancePath": instance_path,
    }
    if target is not None:
        params["target"] = target

    return await bridge.send_command_with_retry(
        command_type="prefab-override",
        parameters=params,
        timeout=timeout,
    )


async def prefab_overrides_revert(
    bridge: DirectBridge,
    instance_path: str,
    target: str | None = None,
    timeout: float = 30.0,
) -> CommandResult:
    """Revert overrides on a prefab instance back to the prefab asset state.

    Args:
        bridge: Active bridge connection.
        instance_path: Hierarchy path to the prefab instance.
        target: Specific override to revert (omit for all).
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {
        "operation": "revert",
        "instancePath": instance_path,
    }
    if target is not None:
        params["target"] = target

    return await bridge.send_command_with_retry(
        command_type="prefab-override",
        parameters=params,
        timeout=timeout,
    )


async def prefab_status(
    bridge: DirectBridge,
    path: str,
    timeout: float = 30.0,
) -> CommandResult:
    """Get prefab type and instance status.

    Args:
        bridge: Active bridge connection.
        path: Hierarchy path or asset path to query.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="prefab-override",
        parameters={
            "operation": "status",
            "instancePath": path,
        },
        timeout=timeout,
    )


async def prefab_find_instances(
    bridge: DirectBridge,
    asset_path: str,
    timeout: float = 30.0,
) -> CommandResult:
    """Find all scene instances of a prefab asset (root-level only).

    NOTE: Does not include nested prefab instances.

    Args:
        bridge: Active bridge connection.
        asset_path: Prefab asset path (e.g. Assets/Prefabs/Enemy.prefab).
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="prefab-override",
        parameters={
            "operation": "find-instances",
            "assetPath": asset_path,
        },
        timeout=timeout,
    )


async def prefab_unpack(
    bridge: DirectBridge,
    instance_path: str,
    completely: bool = False,
    timeout: float = 30.0,
) -> CommandResult:
    """Unpack a prefab instance.

    Args:
        bridge: Active bridge connection.
        instance_path: Hierarchy path to the prefab instance.
        completely: If True, fully unpack nested prefabs.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="prefab-override",
        parameters={
            "operation": "unpack",
            "instancePath": instance_path,
            "completely": completely,
        },
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Phase 2: Prefab override CLI wrappers
# ---------------------------------------------------------------------------

overrides_app = typer.Typer(name="overrides", help="Prefab override management.")
prefab_app.add_typer(overrides_app, name="overrides")


@overrides_app.command("list")
def overrides_list_cli(
    ctx: typer.Context,
    instance_path: Annotated[str, typer.Argument(help="Hierarchy path to prefab instance.")],
    include_default: Annotated[
        bool,
        typer.Option(
            "--include-default-overrides",
            help="Include default overrides (position/rotation).",
        ),
    ] = False,
) -> None:
    """List all overrides on a prefab instance."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(prefab_overrides_list(state.bridge, instance_path, include_default))
    print_result(result, state.formatter)


@overrides_app.command("apply")
def overrides_apply_cli(
    ctx: typer.Context,
    instance_path: Annotated[str, typer.Argument(help="Hierarchy path to prefab instance.")],
    target: Annotated[
        str | None,
        typer.Option("--target", "-t", help="Specific override to apply."),
    ] = None,
) -> None:
    """Apply overrides to the prefab asset."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(prefab_overrides_apply(state.bridge, instance_path, target=target))
    print_result(result, state.formatter)


@overrides_app.command("revert")
def overrides_revert_cli(
    ctx: typer.Context,
    instance_path: Annotated[str, typer.Argument(help="Hierarchy path to prefab instance.")],
    target: Annotated[
        str | None,
        typer.Option("--target", "-t", help="Specific override to revert."),
    ] = None,
) -> None:
    """Revert overrides back to prefab asset state."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(prefab_overrides_revert(state.bridge, instance_path, target=target))
    print_result(result, state.formatter)


@prefab_app.command("status")
def prefab_status_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Hierarchy path or asset path.")],
) -> None:
    """Get prefab type and instance status."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(prefab_status(state.bridge, path))
    print_result(result, state.formatter)


@prefab_app.command("find-instances")
def prefab_find_instances_cli(
    ctx: typer.Context,
    asset_path: Annotated[str, typer.Argument(help="Prefab asset path.")],
) -> None:
    """Find all scene instances of a prefab (root-level only)."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(prefab_find_instances(state.bridge, asset_path))
    print_result(result, state.formatter)


@prefab_app.command("unpack")
def prefab_unpack_cli(
    ctx: typer.Context,
    instance_path: Annotated[str, typer.Argument(help="Hierarchy path to prefab instance.")],
    completely: Annotated[
        bool,
        typer.Option("--completely", help="Fully unpack nested prefabs."),
    ] = False,
) -> None:
    """Unpack a prefab instance."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(prefab_unpack(state.bridge, instance_path, completely=completely))
    print_result(result, state.formatter)

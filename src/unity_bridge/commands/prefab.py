"""Prefab commands: validate, instantiate, destroy."""

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
            "objectPath": instance_path,
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
        raise typer.BadParameter(
            f"Position components must be numbers, got '{value}'"
        ) from exc


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

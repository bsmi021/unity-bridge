"""Build profile commands: list, get-active, set-active, get-info (Unity 6)."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Valid actions
# ---------------------------------------------------------------------------

VALID_ACTIONS = frozenset({"list", "get-active", "set-active", "get-info"})

# ---------------------------------------------------------------------------
# Core async function (CLI + MCP)
# ---------------------------------------------------------------------------


async def build_profile_operation(
    bridge: DirectBridge,
    action: str,
    profile_path: str | None = None,
    timeout: float = 30.0,
) -> CommandResult:
    """Perform a build profile operation.

    Args:
        bridge: Active bridge connection.
        action: Operation — ``list``, ``get-active``, ``set-active``, or ``get-info``.
        profile_path: Asset path to build profile (required for set-active, get-info).
        timeout: Timeout in seconds.

    Raises:
        ValueError: If *action* is not a recognised operation.
    """
    normalised = action.lower().strip()
    if normalised not in VALID_ACTIONS:
        raise ValueError(
            f"Invalid build profile action '{action}'. "
            f"Must be one of: {', '.join(sorted(VALID_ACTIONS))}"
        )

    params: dict[str, object] = {"operation": normalised}
    if profile_path is not None:
        params["profilePath"] = profile_path

    return await bridge.send_command_with_retry(
        command_type="build-profile-operation",
        parameters=params,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrapper
# ---------------------------------------------------------------------------

build_profile_app = typer.Typer(name="profile", help="Unity 6 build profile commands.")


@build_profile_app.command("list")
def profile_list(ctx: typer.Context) -> None:
    """List all build profiles in the project."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(build_profile_operation(state.bridge, "list"))
    print_result(result, state.formatter)


@build_profile_app.command("active")
def profile_active(ctx: typer.Context) -> None:
    """Get the currently active build profile."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(build_profile_operation(state.bridge, "get-active"))
    print_result(result, state.formatter)


@build_profile_app.command("set")
def profile_set(
    ctx: typer.Context,
    path: Annotated[
        str,
        typer.Argument(help="Asset path to build profile."),
    ],
) -> None:
    """Set the active build profile."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(build_profile_operation(state.bridge, "set-active", profile_path=path))
    print_result(result, state.formatter)


@build_profile_app.command("info")
def profile_info(
    ctx: typer.Context,
    path: Annotated[
        str,
        typer.Argument(help="Asset path to build profile."),
    ],
) -> None:
    """Get detailed info about a build profile."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(build_profile_operation(state.bridge, "get-info", profile_path=path))
    print_result(result, state.formatter)

"""Build profile commands: list, get-active, set-active, get-info (Unity 6)."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Valid actions
# ---------------------------------------------------------------------------

VALID_ACTIONS = frozenset(
    {
        "list",
        "get-active",
        "set-active",
        "get-info",
        "get-scenes",
        "set-scenes",
        "get-defines",
        "set-defines",
        "build",
    }
)

# ---------------------------------------------------------------------------
# Core async function (CLI + MCP)
# ---------------------------------------------------------------------------


async def build_profile_operation(
    bridge: DirectBridge,
    action: str,
    profile_path: str | None = None,
    *,
    output_path: str | None = None,
    scenes: list[str] | None = None,
    disabled_scenes: list[str] | None = None,
    scripting_defines: list[str] | None = None,
    development: bool | None = None,
    auto_run_player: bool | None = None,
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
    if output_path is not None:
        params["outputPath"] = output_path
    if scenes is not None:
        params["scenes"] = scenes
    if disabled_scenes is not None:
        params["disabledScenes"] = disabled_scenes
    if scripting_defines is not None:
        params["scriptingDefines"] = scripting_defines
    if development is not None:
        params["development"] = development
    if auto_run_player is not None:
        params["autoRunPlayer"] = auto_run_player

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


@build_profile_app.command("scenes")
def profile_scenes(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Asset path to build profile.")],
) -> None:
    """Get scenes configured on a build profile."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(build_profile_operation(state.bridge, "get-scenes", profile_path=path))
    print_result(result, state.formatter)


@build_profile_app.command("set-scenes")
def profile_set_scenes(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Asset path to build profile.")],
    scene: Annotated[list[str], typer.Option("--scene", help="Enabled scene path.")],
    disabled_scene: Annotated[
        list[str] | None, typer.Option("--disabled-scene", help="Disabled scene path.")
    ] = None,
) -> None:
    """Replace scenes configured on a build profile."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        build_profile_operation(
            state.bridge,
            "set-scenes",
            profile_path=path,
            scenes=scene,
            disabled_scenes=disabled_scene,
        )
    )
    print_result(result, state.formatter)


@build_profile_app.command("defines")
def profile_defines(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Asset path to build profile.")],
) -> None:
    """Get scripting defines configured on a build profile."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(build_profile_operation(state.bridge, "get-defines", profile_path=path))
    print_result(result, state.formatter)


@build_profile_app.command("set-defines")
def profile_set_defines(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Asset path to build profile.")],
    define: Annotated[list[str], typer.Option("--define", help="Scripting define.")],
) -> None:
    """Replace scripting defines configured on a build profile."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        build_profile_operation(
            state.bridge,
            "set-defines",
            profile_path=path,
            scripting_defines=define,
        )
    )
    print_result(result, state.formatter)


@build_profile_app.command("build")
def profile_build(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Asset path to build profile.")],
    output: Annotated[str, typer.Option("--output", help="Build output path.")],
    development: Annotated[bool, typer.Option("--dev")] = False,
    auto_run_player: Annotated[bool, typer.Option("--run")] = False,
) -> None:
    """Build using a build profile's scene list."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        build_profile_operation(
            state.bridge,
            "build",
            profile_path=path,
            output_path=output,
            development=development,
            auto_run_player=auto_run_player,
            timeout=300,
        )
    )
    print_result(result, state.formatter)

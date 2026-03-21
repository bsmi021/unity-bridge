"""Build commands: build, switch-platform, list-platforms, validate, get-settings."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def build(
    bridge: DirectBridge,
    target: str,
    validate_only: bool = False,
    output_path: str | None = None,
    dev: bool = False,
    auto_run: bool = False,
    profiler: bool = False,
    allow_debugging: bool = False,
    compress: str | None = None,
    clean: bool = False,
    detailed_report: bool = False,
    scripts_only: bool = False,
    scenes: list[str] | None = None,
    subtarget: str | None = None,
    timeout: int = 600,
) -> CommandResult:
    """Start a Unity build for the specified target platform.

    Args:
        bridge: Active bridge connection.
        target: Build target platform (e.g. ``StandaloneWindows64``, ``Android``).
        validate_only: If True, validate without building.
        output_path: Build output path.
        dev: Enable development build.
        auto_run: Auto-run player after build.
        profiler: Connect profiler to build.
        allow_debugging: Allow script debugging.
        compress: Compression mode (lz4, lz4hc).
        clean: Clean build cache before building.
        detailed_report: Generate detailed build report.
        scripts_only: Build scripts only (no player).
        scenes: Custom scene list (overrides Build Settings).
        subtarget: Build subtarget (Server, Player).
        timeout: Timeout in seconds.
    """
    operation = "validate" if validate_only else "build"
    params: dict[str, object] = {"operation": operation, "target": target}
    if output_path is not None:
        params["outputPath"] = output_path
    if dev:
        params["development"] = True
    if auto_run:
        params["autoRunPlayer"] = True
    if profiler:
        params["connectProfiler"] = True
    if allow_debugging:
        params["allowDebugging"] = True
    if compress:
        params["compress"] = compress
    if clean:
        params["cleanBuildCache"] = True
    if detailed_report:
        params["detailedBuildReport"] = True
    if scripts_only:
        params["buildScriptsOnly"] = True
    if scenes:
        params["scenes"] = scenes
    if subtarget:
        params["subtarget"] = subtarget

    return await bridge.send_command_with_retry(
        command_type="build-operation",
        parameters=params,
        timeout=float(timeout),
    )


async def switch_platform(
    bridge: DirectBridge,
    target: str,
    timeout: float = 120.0,
) -> CommandResult:
    """Switch the active build platform. Triggers domain reload.

    Args:
        bridge: Active bridge connection.
        target: Build target platform (e.g. ``Android``, ``WebGL``).
        timeout: Timeout in seconds (longer due to domain reload).
    """
    return await bridge.send_command_with_retry(
        command_type="build-operation",
        parameters={"operation": "switch-platform", "target": target},
        timeout=timeout,
    )


async def list_platforms(
    bridge: DirectBridge,
    timeout: float = 15.0,
) -> CommandResult:
    """List all known build platforms and their support status.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="build-operation",
        parameters={"operation": "list-platforms"},
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI
# ---------------------------------------------------------------------------

build_app = typer.Typer(name="build", help="Unity build commands.")


@build_app.callback(invoke_without_command=True)
def build_cli(
    ctx: typer.Context,
    target: Annotated[
        str,
        typer.Option("--target", "-T", help="Build target platform."),
    ] = "",
    validate_only: Annotated[
        bool,
        typer.Option("--validate-only", help="Validate config without building."),
    ] = False,
    output: Annotated[
        str | None,
        typer.Option("--output", "-o", help="Build output path."),
    ] = None,
    dev: Annotated[
        bool,
        typer.Option("--dev", help="Development build with debugging."),
    ] = False,
    auto_run: Annotated[
        bool,
        typer.Option("--auto-run", help="Auto-run player after build."),
    ] = False,
    profiler_opt: Annotated[
        bool,
        typer.Option("--profiler", help="Connect profiler to build."),
    ] = False,
    compress: Annotated[
        str | None,
        typer.Option("--compress", help="Compression: lz4, lz4hc."),
    ] = None,
    scenes: Annotated[
        str | None,
        typer.Option("--scenes", help="Comma-separated scene paths."),
    ] = None,
    subtarget: Annotated[
        str | None,
        typer.Option("--subtarget", help="Subtarget: Server, Player."),
    ] = None,
    timeout: Annotated[
        int,
        typer.Option("--timeout", help="Timeout in seconds."),
    ] = 600,
) -> None:
    """Build the Unity project for a target platform."""
    if ctx.invoked_subcommand is not None:
        return
    if not target:
        raise typer.BadParameter("--target is required for build.")
    from unity_bridge.core.output import print_result

    scene_list = scenes.split(",") if scenes else None
    state = ctx.obj
    result = asyncio.run(
        build(
            state.bridge,
            target,
            validate_only,
            output,
            dev,
            auto_run,
            profiler_opt,
            False,
            compress,
            False,
            False,
            False,
            scene_list,
            subtarget,
            timeout,
        )
    )
    print_result(result, state.formatter)


@build_app.command("switch-platform")
def switch_platform_cli(
    ctx: typer.Context,
    target: Annotated[str, typer.Argument(help="Target platform to switch to.")],
    timeout: Annotated[
        int, typer.Option("--timeout", help="Timeout in seconds.")
    ] = 120,
) -> None:
    """Switch the active build platform (triggers domain reload)."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(switch_platform(state.bridge, target, float(timeout)))
    print_result(result, state.formatter)


@build_app.command("list-platforms")
def list_platforms_cli(
    ctx: typer.Context,
    timeout: Annotated[
        int, typer.Option("--timeout", help="Timeout in seconds.")
    ] = 15,
) -> None:
    """List all known build platforms and their support status."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(list_platforms(state.bridge, float(timeout)))
    print_result(result, state.formatter)

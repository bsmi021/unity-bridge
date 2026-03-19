"""Build command: build --target TARGET [--validate-only]."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async function (CLI + MCP)
# ---------------------------------------------------------------------------


async def build(
    bridge: DirectBridge,
    target: str,
    validate_only: bool = False,
    output_path: str | None = None,
    dev: bool = False,
    timeout: int = 600,
) -> CommandResult:
    """Start a Unity build for the specified target platform.

    Args:
        bridge: Active bridge connection.
        target: Build target platform (e.g. ``StandaloneWindows64``, ``Android``).
        validate_only: If True, validate the build configuration without building.
        output_path: Directory or file path for the build output.
        dev: Enable development build with debugging support.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {"target": target}
    if validate_only:
        params["validateOnly"] = True
    if output_path is not None:
        params["outputPath"] = output_path
    if dev:
        params["developmentBuild"] = True

    return await bridge.send_command_with_retry(
        command_type="build-operation",
        parameters=params,
        timeout=float(timeout),
    )


# ---------------------------------------------------------------------------
# Typer CLI wrapper
# ---------------------------------------------------------------------------

build_app = typer.Typer(name="build", help="Unity build commands.")


@build_app.callback(invoke_without_command=True)
def build_cli(
    ctx: typer.Context,
    target: Annotated[
        str,
        typer.Option(
            "--target", "-T",
            help="Build target platform (e.g. StandaloneWindows64, Android).",
        ),
    ],
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
    timeout: Annotated[
        int,
        typer.Option("--timeout", help="Timeout in seconds."),
    ] = 600,
) -> None:
    """Build the Unity project for a target platform."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        build(state.bridge, target, validate_only, output, dev, timeout)
    )
    print_result(result, state.formatter)

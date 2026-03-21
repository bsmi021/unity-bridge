"""Compilation pipeline commands: assemblies, defines, which, optimization.

Separate from ``compile.py`` which handles triggering script compilation.
This module queries assembly structure, scripting defines, script ownership,
and code optimization settings via the ``compilation-pipeline`` command type.
"""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Valid operations
# ---------------------------------------------------------------------------

VALID_OPERATIONS = frozenset({"assemblies", "defines", "which", "optimization"})

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def compile_assemblies(
    bridge: DirectBridge,
    timeout: float = 15.0,
) -> CommandResult:
    """List all project assemblies with metadata.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="compilation-pipeline",
        parameters={"operation": "assemblies"},
        timeout=timeout,
    )


async def compile_defines(
    bridge: DirectBridge,
    assembly_name: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Get scripting defines for a named assembly.

    Args:
        bridge: Active bridge connection.
        assembly_name: Assembly name (e.g. ``Assembly-CSharp``).
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="compilation-pipeline",
        parameters={"operation": "defines", "assemblyName": assembly_name},
        timeout=timeout,
    )


async def compile_which(
    bridge: DirectBridge,
    script_path: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Determine which assembly owns a given script.

    Args:
        bridge: Active bridge connection.
        script_path: Asset path to the script file.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="compilation-pipeline",
        parameters={"operation": "which", "scriptPath": script_path},
        timeout=timeout,
    )


async def compile_optimization(
    bridge: DirectBridge,
    mode: str | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Get or set the code optimization level.

    Args:
        bridge: Active bridge connection.
        mode: Optimization mode to set (``None``, ``Debug``, ``Release``).
              Omit to query current mode.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {"operation": "optimization"}
    if mode is not None:
        params["mode"] = mode

    return await bridge.send_command_with_retry(
        command_type="compilation-pipeline",
        parameters=params,
        timeout=timeout,
    )


async def compilation_pipeline_operation(
    bridge: DirectBridge,
    operation: str,
    assembly_name: str | None = None,
    script_path: str | None = None,
    mode: str | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Generic compilation pipeline operation (used by MCP dispatch).

    Args:
        bridge: Active bridge connection.
        operation: Operation — ``assemblies``, ``defines``, ``which``,
                   or ``optimization``.
        assembly_name: Assembly name (for ``defines`` operation).
        script_path: Script asset path (for ``which`` operation).
        mode: Optimization mode (for ``optimization`` set operation).
        timeout: Timeout in seconds.

    Raises:
        ValueError: If *operation* is not recognised.
    """
    normalised = operation.lower().strip()
    if normalised not in VALID_OPERATIONS:
        raise ValueError(
            f"Invalid compilation pipeline operation '{operation}'. "
            f"Must be one of: {', '.join(sorted(VALID_OPERATIONS))}"
        )

    params: dict[str, object] = {"operation": normalised}
    if assembly_name is not None:
        params["assemblyName"] = assembly_name
    if script_path is not None:
        params["scriptPath"] = script_path
    if mode is not None:
        params["mode"] = mode

    return await bridge.send_command_with_retry(
        command_type="compilation-pipeline",
        parameters=params,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

compile_ext_app = typer.Typer(
    name="compile",
    help="Compilation pipeline query commands.",
)


@compile_ext_app.command("assemblies")
def compile_assemblies_cli(ctx: typer.Context) -> None:
    """List all project assemblies with metadata."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(compile_assemblies(state.bridge))
    print_result(result, state.formatter)


@compile_ext_app.command("defines")
def compile_defines_cli(
    ctx: typer.Context,
    assembly: Annotated[
        str,
        typer.Argument(help="Assembly name (e.g. Assembly-CSharp)."),
    ],
) -> None:
    """Get scripting defines for a named assembly."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(compile_defines(state.bridge, assembly))
    print_result(result, state.formatter)


@compile_ext_app.command("which")
def compile_which_cli(
    ctx: typer.Context,
    script_path: Annotated[
        str,
        typer.Argument(help="Script asset path (e.g. Assets/Scripts/Player.cs)."),
    ],
) -> None:
    """Determine which assembly owns a script file."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(compile_which(state.bridge, script_path))
    print_result(result, state.formatter)


@compile_ext_app.command("optimization")
def compile_optimization_cli(
    ctx: typer.Context,
    set_mode: Annotated[
        str | None,
        typer.Option("--set", help="Set optimization mode: None, Debug, or Release."),
    ] = None,
) -> None:
    """Get or set the code optimization level."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(compile_optimization(state.bridge, mode=set_mode))
    print_result(result, state.formatter)

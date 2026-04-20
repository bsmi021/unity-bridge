"""Sync IDE solution / project files.

Regenerates .sln / .csproj so the IDE sees current assembly definitions,
scripts, and references. Use after adding scripts or editing .asmdef
files when the IDE is not picking up changes.
"""

from __future__ import annotations

import asyncio

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge


async def sync_solution(
    bridge: DirectBridge,
    timeout: float = 30.0,
) -> CommandResult:
    """Regenerate the Unity project's IDE solution/project files."""
    return await bridge.send_command_with_retry(
        command_type="sync-solution",
        parameters={},
        timeout=timeout,
    )


def sync_solution_cli(ctx: typer.Context) -> None:
    """Regenerate .sln/.csproj files for the current Unity project."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(sync_solution(state.bridge))
    print_result(result, state.formatter)

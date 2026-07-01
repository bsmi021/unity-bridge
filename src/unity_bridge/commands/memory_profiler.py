"""Memory profiler commands: take-snapshot (Unity.Profiling.Memory.MemoryProfiler)."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def memory_profiler_take_snapshot(
    bridge: DirectBridge,
    path: str | None = None,
    capture_flags: str | None = None,
    timeout: float = 120.0,
) -> CommandResult:
    """Capture a Unity memory snapshot via MemoryProfiler.TakeSnapshot.

    Args:
        bridge: Active bridge connection.
        path: Destination path for the .snap file. If omitted, the Unity
            handler chooses a default path under
            ``.claude/unity/memory-snapshots/``.
        capture_flags: Comma-separated Unity.Profiling.Memory.CaptureFlags
            names (e.g. "ManagedObjects,NativeObjects"). If omitted, the
            Unity handler uses its own default flag combination.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {"operation": "take-snapshot"}
    if path is not None:
        params["path"] = path
    if capture_flags is not None:
        params["captureFlags"] = capture_flags

    return await bridge.send_command_with_retry(
        command_type="memory-profiler",
        parameters=params,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

memory_profiler_app = typer.Typer(
    name="memory-profiler", help="Unity memory snapshot capture commands."
)


@memory_profiler_app.callback()
def memory_profiler_main() -> None:
    """Unity memory snapshot capture commands."""


@memory_profiler_app.command("take-snapshot")
def memory_profiler_take_snapshot_cli(
    ctx: typer.Context,
    path: Annotated[
        str | None,
        typer.Option("--path", help="Destination path for the .snap file."),
    ] = None,
    capture_flags: Annotated[
        str | None,
        typer.Option(
            "--capture-flags",
            help="Comma-separated CaptureFlags names (e.g. ManagedObjects,NativeObjects).",
        ),
    ] = None,
) -> None:
    """Capture a Unity memory snapshot."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        memory_profiler_take_snapshot(state.bridge, path=path, capture_flags=capture_flags)
    )
    print_result(result, state.formatter)

"""Batch command: execute multiple Unity commands from a JSON file."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated, Any

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge
from unity_bridge.core.protocol import is_parallel_safe

# ---------------------------------------------------------------------------
# Core async function (CLI + MCP)
# ---------------------------------------------------------------------------


async def batch_execute(
    bridge: DirectBridge,
    commands: list[dict[str, Any]],
    stop_on_error: bool = True,
    parallel: bool = False,
) -> CommandResult:
    """Execute a list of bridge commands sequentially or in parallel.

    Args:
        bridge: Active bridge connection.
        commands: List of command dicts with ``type`` and optional ``parameters``.
        stop_on_error: Halt execution on the first failure.
        parallel: Run read-only commands concurrently; unsafe commands run sequentially.
    """
    if parallel:
        results = await _execute_parallel(bridge, commands, stop_on_error)
    else:
        results = await _execute_sequential(bridge, commands, stop_on_error)

    success_count = sum(1 for r in results if r.get("result", {}).get("success"))
    return CommandResult(
        success=success_count == len(results),
        data={
            "total_commands": len(commands),
            "executed_commands": len(results),
            "success_count": success_count,
            "failure_count": len(results) - success_count,
            "results": results,
        },
    )


# ---------------------------------------------------------------------------
# Execution strategies
# ---------------------------------------------------------------------------


async def _execute_sequential(
    bridge: DirectBridge,
    commands: list[dict[str, Any]],
    stop_on_error: bool,
) -> list[dict[str, Any]]:
    """Run commands one at a time."""
    results: list[dict[str, Any]] = []
    for cmd in commands:
        cmd_type = cmd.get("type", "unknown")
        timeout = float(cmd.get("timeout", 30))
        result = await bridge.send_command(
            cmd_type, cmd.get("parameters", {}), timeout=timeout,
        )
        entry = _build_result_entry(cmd, result)
        results.append(entry)
        if stop_on_error and not result.success:
            break
    return results


async def _execute_parallel(
    bridge: DirectBridge,
    commands: list[dict[str, Any]],
    stop_on_error: bool,
) -> list[dict[str, Any]]:
    """Run parallel-safe commands concurrently, unsafe ones sequentially."""
    safe: list[dict[str, Any]] = []
    unsafe: list[dict[str, Any]] = []
    for cmd in commands:
        if is_parallel_safe(cmd.get("type", ""), cmd.get("parameters")):
            safe.append(cmd)
        else:
            unsafe.append(cmd)

    results: list[dict[str, Any]] = []

    # Execute safe commands concurrently
    if safe:
        tasks = [
            bridge.send_command(
                cmd["type"], cmd.get("parameters", {}),
                timeout=float(cmd.get("timeout", 30)),
            )
            for cmd in safe
        ]
        raw = await asyncio.gather(*tasks, return_exceptions=True)
        for cmd, res in zip(safe, raw):
            if isinstance(res, Exception):
                entry = _build_error_entry(cmd, str(res))
            else:
                entry = _build_result_entry(cmd, res)
            results.append(entry)

    # Execute unsafe commands sequentially
    for cmd in unsafe:
        cmd_type = cmd.get("type", "unknown")
        timeout = float(cmd.get("timeout", 30))
        result = await bridge.send_command(
            cmd_type, cmd.get("parameters", {}), timeout=timeout,
        )
        entry = _build_result_entry(cmd, result)
        results.append(entry)
        if stop_on_error and not result.success:
            break

    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_result_entry(cmd: dict[str, Any], result: CommandResult) -> dict[str, Any]:
    """Build a per-command result dict."""
    return {
        "id": cmd.get("id", cmd.get("type", "unknown")),
        "type": cmd.get("type", "unknown"),
        "result": {
            "success": result.success,
            "data": result.data,
            "error": result.error,
        },
    }


def _build_error_entry(cmd: dict[str, Any], error: str) -> dict[str, Any]:
    """Build an error result dict for a failed command."""
    return {
        "id": cmd.get("id", cmd.get("type", "unknown")),
        "type": cmd.get("type", "unknown"),
        "result": {"success": False, "error": error},
    }


def _load_batch_file(path: Path) -> list[dict[str, Any]]:
    """Load and validate a batch JSON file."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"Invalid JSON in batch file: {exc}") from exc
    except OSError as exc:
        raise typer.BadParameter(f"Cannot read batch file: {exc}") from exc

    if isinstance(data, dict):
        commands = data.get("commands", [])
    elif isinstance(data, list):
        commands = data
    else:
        raise typer.BadParameter("Batch file must be a JSON array or object with 'commands' key.")

    if not isinstance(commands, list) or not commands:
        raise typer.BadParameter("Batch file contains no commands.")

    for i, cmd in enumerate(commands):
        if not isinstance(cmd, dict) or "type" not in cmd:
            raise typer.BadParameter(f"Command at index {i} must be an object with a 'type' key.")

    return commands


# ---------------------------------------------------------------------------
# Typer CLI wrapper
# ---------------------------------------------------------------------------

batch_app = typer.Typer(name="batch", help="Execute multiple commands from a JSON file.")


@batch_app.callback(invoke_without_command=True)
def batch_cli(
    ctx: typer.Context,
    file: Annotated[
        Path, typer.Argument(help="Path to the batch JSON file.")
    ],
    stop_on_error: Annotated[
        bool,
        typer.Option("--stop-on-error/--no-stop-on-error", help="Halt on first failure."),
    ] = True,
    parallel: Annotated[
        bool,
        typer.Option("--parallel", help="Run read-only commands concurrently."),
    ] = False,
) -> None:
    """Execute multiple Unity commands from a JSON file."""
    from unity_bridge.core.output import print_result

    commands = _load_batch_file(file)
    state = ctx.obj
    result = asyncio.run(
        batch_execute(state.bridge, commands, stop_on_error, parallel)
    )
    print_result(result, state.formatter)

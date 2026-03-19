"""Console commands: read, watch, clear.

``console watch`` implements follow-mode by polling until interrupted.
"""

from __future__ import annotations

import asyncio
import signal
import sys
import time
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def console_read(
    bridge: DirectBridge,
    types: str | None = None,
    max_entries: int | None = None,
    pattern: str | None = None,
    stack_trace: bool = False,
    max_stack_lines: int | None = None,
    max_message_length: int | None = None,
    timeout: float = 10.0,
) -> CommandResult:
    """Read console log entries from the Unity Editor.

    Args:
        bridge: Active bridge connection.
        types: Comma-separated log types to include (e.g. ``error,warning,log``).
        max_entries: Maximum number of entries to return.
        pattern: Regex pattern to filter messages.
        stack_trace: Include stack traces in the output.
        max_stack_lines: Limit stack trace lines per entry.
        max_message_length: Truncate messages to this length.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {}
    if types is not None:
        params["logTypes"] = types
    if max_entries is not None:
        params["maxEntries"] = max_entries
    if pattern is not None:
        params["filterPattern"] = pattern
    if stack_trace:
        params["includeStackTrace"] = True
    if max_stack_lines is not None:
        params["maxStackLines"] = max_stack_lines
    if max_message_length is not None:
        params["maxMessageLength"] = max_message_length

    return await bridge.send_command_with_retry(
        command_type="read-console",
        parameters=params,
        timeout=timeout,
    )


async def console_clear(
    bridge: DirectBridge,
    timeout: float = 5.0,
) -> CommandResult:
    """Clear the Unity Editor console.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="clear-console",
        parameters={},
        timeout=timeout,
    )


async def console_watch(
    bridge: DirectBridge,
    types: str | None = None,
    poll_interval: float = 2.0,
    timeout: float = 10.0,
) -> None:
    """Follow console output, printing new entries until interrupted.

    This is a long-running operation intended for CLI use. It polls the
    console repeatedly and prints any new entries to stdout. Stop with
    ``Ctrl+C``.

    Args:
        bridge: Active bridge connection.
        types: Comma-separated log types to watch.
        poll_interval: Seconds between polls.
        timeout: Per-poll timeout in seconds.
    """
    from unity_bridge.core.output import print_result, OutputFormatter

    formatter = OutputFormatter(format="json", color=True)
    seen_count = 0

    while True:
        result = await console_read(
            bridge,
            types=types,
            timeout=timeout,
        )

        if result.success and result.data:
            entries = _extract_entries(result.data)
            new_entries = entries[seen_count:]
            if new_entries:
                seen_count = len(entries)
                for entry in new_entries:
                    _print_console_entry(entry)

        await asyncio.sleep(poll_interval)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_entries(data: object) -> list[dict[str, object]]:
    """Safely extract log entries from response data."""
    if isinstance(data, dict):
        entries = data.get("entries", data.get("logs", []))
        if isinstance(entries, list):
            return entries
    if isinstance(data, list):
        return data
    return []


def _print_console_entry(entry: dict[str, object]) -> None:
    """Print a single console log entry to stdout."""
    log_type = str(entry.get("type", entry.get("logType", "LOG"))).upper()
    message = str(entry.get("message", entry.get("condition", "")))

    prefix_map = {"ERROR": "[ERR]", "WARNING": "[WRN]", "LOG": "[LOG]"}
    prefix = prefix_map.get(log_type, f"[{log_type}]")

    sys.stdout.write(f"{prefix} {message}\n")
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

console_app = typer.Typer(name="console", help="Unity Editor console commands.")


@console_app.command("read")
def console_read_cli(
    ctx: typer.Context,
    types: Annotated[
        str | None,
        typer.Option("--types", "-T", help="Comma-separated log types (error,warning,log)."),
    ] = None,
    max_entries: Annotated[
        int | None,
        typer.Option("--max", "-m", help="Maximum entries to return."),
    ] = None,
    pattern: Annotated[
        str | None,
        typer.Option("--pattern", "-p", help="Regex filter pattern for messages."),
    ] = None,
    stack_trace: Annotated[
        bool,
        typer.Option("--stack-trace", help="Include stack traces."),
    ] = False,
    max_stack_lines: Annotated[
        int | None,
        typer.Option("--max-stack-lines", help="Max stack trace lines per entry."),
    ] = None,
    max_message_length: Annotated[
        int | None,
        typer.Option("--max-message-length", help="Truncate messages to this length."),
    ] = None,
) -> None:
    """Read console log entries from Unity."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        console_read(
            state.bridge,
            types=types,
            max_entries=max_entries,
            pattern=pattern,
            stack_trace=stack_trace,
            max_stack_lines=max_stack_lines,
            max_message_length=max_message_length,
        )
    )
    print_result(result, state.formatter)


@console_app.command("watch")
def console_watch_cli(
    ctx: typer.Context,
    types: Annotated[
        str | None,
        typer.Option("--types", "-T", help="Comma-separated log types to watch."),
    ] = None,
    poll_interval: Annotated[
        float,
        typer.Option("--poll-interval", help="Seconds between polls."),
    ] = 2.0,
) -> None:
    """Follow console output in real time (Ctrl+C to stop)."""
    state = ctx.obj

    def _handle_sigint(_signum: int, _frame: object) -> None:
        sys.stdout.write("\nWatch stopped.\n")
        sys.stdout.flush()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _handle_sigint)

    try:
        asyncio.run(
            console_watch(state.bridge, types=types, poll_interval=poll_interval)
        )
    except (KeyboardInterrupt, SystemExit):
        pass


@console_app.command("clear")
def console_clear_cli(ctx: typer.Context) -> None:
    """Clear the Unity Editor console."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(console_clear(state.bridge))
    print_result(result, state.formatter)

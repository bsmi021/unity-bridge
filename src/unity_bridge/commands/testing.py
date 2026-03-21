"""Testing commands: test run, compile, test listing.

Async core functions are shared between CLI and MCP entry points.
Typer wrappers provide the CLI surface with ``asyncio.run()``.
"""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Valid list modes
# ---------------------------------------------------------------------------

VALID_LIST_MODES = frozenset({"tests", "categories", "assemblies"})

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def run_tests(
    bridge: DirectBridge,
    platform: str = "EditMode",
    filter_pattern: str | None = None,
    timeout: int = 300,
) -> CommandResult:
    """Run Unity Test Runner tests.

    Args:
        bridge: Active bridge connection.
        platform: Test platform — ``EditMode`` or ``PlayMode``.
        filter_pattern: Optional filter to restrict which tests run.
        timeout: Maximum seconds to wait for results.

    Returns:
        CommandResult with test outcome data.
    """
    params: dict[str, object] = {"testPlatform": platform}
    if filter_pattern is not None:
        params["testFilter"] = filter_pattern

    return await bridge.send_command_with_retry(
        command_type="run-tests",
        parameters=params,
        timeout=float(timeout),
    )


async def list_tests(
    bridge: DirectBridge,
    mode: str = "tests",
    platform: str | None = None,
    filter_pattern: str | None = None,
    timeout: float = 30.0,
) -> CommandResult:
    """Discover available tests without executing them.

    Args:
        bridge: Active bridge connection.
        mode: What to list — ``tests``, ``categories``, or ``assemblies``.
        platform: Test platform filter (``EditMode`` or ``PlayMode``).
        filter_pattern: Test name filter pattern.
        timeout: Timeout in seconds.

    Raises:
        ValueError: If *mode* is not recognised.
    """
    normalised = mode.lower().strip()
    if normalised not in VALID_LIST_MODES:
        raise ValueError(
            f"Invalid list mode '{mode}'. Must be one of: {', '.join(sorted(VALID_LIST_MODES))}"
        )

    params: dict[str, object] = {"mode": normalised}
    if platform is not None:
        params["testPlatform"] = platform
    if filter_pattern is not None:
        params["filter"] = filter_pattern

    return await bridge.send_command_with_retry(
        command_type="list-tests",
        parameters=params,
        timeout=timeout,
    )


async def compile_scripts(
    bridge: DirectBridge,
    wait: bool = True,
    timeout: int = 120,
) -> CommandResult:
    """Trigger a script compilation in the Unity Editor.

    Args:
        bridge: Active bridge connection.
        wait: If ``True``, block until compilation finishes.
        timeout: Maximum seconds to wait for compilation.

    Returns:
        CommandResult with compilation status.
    """
    return await bridge.send_command_with_retry(
        command_type="compile",
        parameters={"waitForCompletion": wait},
        timeout=float(timeout),
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

test_app = typer.Typer(name="test", help="Unity Test Runner commands.")


@test_app.command("run")
def test_run_cli(
    ctx: typer.Context,
    platform: Annotated[
        str,
        typer.Option("--platform", "-P", help="Test platform: EditMode or PlayMode."),
    ] = "EditMode",
    filter_pattern: Annotated[
        str | None,
        typer.Option("--filter", "-f", help="Filter pattern for test names."),
    ] = None,
    timeout: Annotated[
        int,
        typer.Option("--timeout", help="Timeout in seconds."),
    ] = 300,
) -> None:
    """Run tests via the Unity Test Runner."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(run_tests(state.bridge, platform, filter_pattern, timeout))
    print_result(result, state.formatter)


@test_app.command("list")
def test_list_cli(
    ctx: typer.Context,
    platform: Annotated[
        str | None,
        typer.Option("--platform", "-P", help="Test platform: EditMode or PlayMode."),
    ] = None,
    filter_pattern: Annotated[
        str | None,
        typer.Option("--filter", "-f", help="Filter pattern for test names."),
    ] = None,
    categories: Annotated[
        bool,
        typer.Option("--categories", help="List test categories instead of tests."),
    ] = False,
    assemblies: Annotated[
        bool,
        typer.Option("--assemblies", help="List test assemblies instead of tests."),
    ] = False,
) -> None:
    """Discover available tests without executing them."""
    from unity_bridge.core.output import print_result

    mode = "tests"
    if categories:
        mode = "categories"
    elif assemblies:
        mode = "assemblies"

    state = ctx.obj
    result = asyncio.run(list_tests(state.bridge, mode, platform, filter_pattern))
    print_result(result, state.formatter)


@test_app.command("compile")
def compile_cli(
    ctx: typer.Context,
    wait: Annotated[
        bool,
        typer.Option("--wait/--no-wait", help="Wait for compilation to finish."),
    ] = True,
    timeout: Annotated[
        int,
        typer.Option("--timeout", help="Timeout in seconds."),
    ] = 120,
) -> None:
    """Trigger script compilation in Unity."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(compile_scripts(state.bridge, wait, timeout))
    print_result(result, state.formatter)

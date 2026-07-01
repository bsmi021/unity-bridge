"""Testing commands: test run, compile, test listing.

Async core functions are shared between CLI and MCP entry points.
Typer wrappers provide the CLI surface with ``asyncio.run()``.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Annotated

import typer

from unity_bridge.commands.test_artifacts import (
    list_test_result_history,
    read_test_failures_artifact,
    read_test_progress_artifact,
    read_test_progress_events,
    read_test_result_artifact,
)
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
    test_names: list[str] | None = None,
    group_names: list[str] | None = None,
    categories: list[str] | None = None,
    assemblies: list[str] | None = None,
    min_tests: int = 0,
) -> CommandResult:
    """Run Unity Test Runner tests.

    Args:
        bridge: Active bridge connection.
        platform: Test platform — ``EditMode`` or ``PlayMode``.
        filter_pattern: Optional filter to restrict which tests run.
        timeout: Maximum seconds to wait for results.
        test_names: Full test names to execute.
        group_names: Regex-style group names/namespaces to execute.
        categories: NUnit categories to include.
        assemblies: Test assembly names to include.
        min_tests: Minimum number of executed tests required for success.

    Returns:
        CommandResult with test outcome data.
    """
    params: dict[str, object] = {"testPlatform": platform}
    if filter_pattern is not None:
        params["testFilter"] = filter_pattern
    _add_selector(params, "testNames", test_names)
    _add_selector(params, "groupNames", group_names)
    _add_selector(params, "categoryNames", categories)
    _add_selector(params, "assemblyNames", assemblies)

    result = await bridge.send_command_with_retry(
        command_type="run-tests",
        parameters=params,
        timeout=float(timeout),
    )
    return _enforce_min_tests(result, min_tests)


async def cancel_tests(
    bridge: DirectBridge,
    command_id: str | None = None,
    timeout: int = 10,
) -> CommandResult:
    """Request cancellation of an active Unity Test Runner run."""
    params: dict[str, object] = {}
    if command_id:
        params["targetCommandId"] = command_id

    return await bridge.send_command_with_retry(
        command_type="cancel-tests",
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


async def preflight_tests(
    bridge: DirectBridge,
    platform: str = "EditMode",
    filter_pattern: str | None = None,
    timeout: int = 30,
    test_names: list[str] | None = None,
    group_names: list[str] | None = None,
    categories: list[str] | None = None,
    assemblies: list[str] | None = None,
    min_tests: int = 1,
) -> CommandResult:
    """Discover and validate tests before running them."""
    group_patterns = _compile_group_patterns(group_names)
    if isinstance(group_patterns, CommandResult):
        return group_patterns

    discovery = await list_tests(
        bridge,
        mode="tests",
        platform=platform,
        filter_pattern=filter_pattern,
        timeout=float(timeout),
    )
    if not discovery.success:
        return _preflight_discovery_failure(discovery)

    tests = _discovered_tests(discovery.data)
    selected = _select_preflight_tests(
        tests,
        test_names=test_names,
        group_patterns=group_patterns,
        categories=categories,
        assemblies=assemblies,
    )
    return _preflight_result(
        discovery,
        tests,
        selected,
        platform=platform,
        filter_pattern=filter_pattern,
        min_tests=min_tests,
        selectors={
            "testNames": test_names or [],
            "groupNames": group_names or [],
            "categoryNames": categories or [],
            "assemblyNames": assemblies or [],
        },
    )


async def rerun_failed_tests(
    bridge: DirectBridge,
    project_root: Path,
    command_id: str | None = None,
    platform: str = "EditMode",
    timeout: int = 300,
) -> CommandResult:
    """Rerun failed tests from a durable test result artifact."""
    failures = read_test_failures_artifact(project_root, command_id)
    if not failures.success:
        return failures

    payload = failures.data or {}
    test_names = _failed_test_names(payload.get("failures", []))
    if not test_names:
        return CommandResult(
            success=True,
            data={
                "commandId": payload.get("commandId"),
                "rerunCount": 0,
                "testNames": [],
                "message": "No failed tests found to rerun.",
            },
        )

    result = await run_tests(
        bridge,
        platform=platform,
        timeout=timeout,
        test_names=test_names,
    )
    if isinstance(result.data, dict):
        result.data.setdefault("rerunSourceCommandId", payload.get("commandId"))
        result.data.setdefault("rerunCount", len(test_names))
        result.data.setdefault("rerunTestNames", test_names)
    return result


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
    test_names: Annotated[
        list[str] | None,
        typer.Option(
            "--test-name",
            help="Full test name to execute. Can be passed multiple times.",
        ),
    ] = None,
    group_names: Annotated[
        list[str] | None,
        typer.Option(
            "--group",
            help="Regex-style fixture/namespace group to execute. Can be passed multiple times.",
        ),
    ] = None,
    categories: Annotated[
        list[str] | None,
        typer.Option(
            "--category",
            help="NUnit category to include. Can be passed multiple times.",
        ),
    ] = None,
    assemblies: Annotated[
        list[str] | None,
        typer.Option(
            "--assembly",
            help="Test assembly name without .dll. Can be passed multiple times.",
        ),
    ] = None,
    min_tests: Annotated[
        int,
        typer.Option("--min-tests", help="Minimum executed test count required for success."),
    ] = 0,
) -> None:
    """Run tests via the Unity Test Runner."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        run_tests(
            state.bridge,
            platform=platform,
            filter_pattern=filter_pattern,
            timeout=timeout,
            test_names=test_names,
            group_names=group_names,
            categories=categories,
            assemblies=assemblies,
            min_tests=min_tests,
        )
    )
    print_result(result, state.formatter)


@test_app.command("cancel")
def test_cancel_cli(
    ctx: typer.Context,
    command_id: Annotated[
        str | None,
        typer.Option(
            "--command-id",
            help="Bridge run-tests command id to cancel. Defaults to the active test run.",
        ),
    ] = None,
    timeout: Annotated[
        int,
        typer.Option("--timeout", help="Timeout in seconds."),
    ] = 10,
) -> None:
    """Cancel an active bridge-initiated Unity Test Runner run."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(cancel_tests(state.bridge, command_id=command_id, timeout=timeout))
    print_result(result, state.formatter)


@test_app.command("preflight")
def test_preflight_cli(
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
        typer.Option("--timeout", help="Discovery timeout in seconds."),
    ] = 30,
    test_names: Annotated[
        list[str] | None,
        typer.Option(
            "--test-name",
            help="Full test name expected to be discoverable. Can be passed multiple times.",
        ),
    ] = None,
    group_names: Annotated[
        list[str] | None,
        typer.Option(
            "--group",
            help="Regex-style fixture/namespace group expected. Can be passed multiple times.",
        ),
    ] = None,
    categories: Annotated[
        list[str] | None,
        typer.Option(
            "--category",
            help="NUnit category expected to be discoverable. Can be passed multiple times.",
        ),
    ] = None,
    assemblies: Annotated[
        list[str] | None,
        typer.Option(
            "--assembly",
            help="Test assembly name expected. Can be passed multiple times.",
        ),
    ] = None,
    min_tests: Annotated[
        int,
        typer.Option("--min-tests", help="Minimum selected test count required."),
    ] = 1,
) -> None:
    """Discover and validate tests before running them."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        preflight_tests(
            state.bridge,
            platform=platform,
            filter_pattern=filter_pattern,
            timeout=timeout,
            test_names=test_names,
            group_names=group_names,
            categories=categories,
            assemblies=assemblies,
            min_tests=min_tests,
        )
    )
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


@test_app.command("results")
def test_results_cli(
    ctx: typer.Context,
    command_id: Annotated[
        str | None,
        typer.Option("--command-id", help="Specific bridge command id to read."),
    ] = None,
    last: Annotated[
        bool,
        typer.Option("--last", help="Read the latest test result artifact."),
    ] = False,
) -> None:
    """Read a durable test result artifact without contacting Unity."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    selected_id = None if last else command_id
    result = read_test_result_artifact(state.project_root, selected_id)
    print_result(result, state.formatter)


@test_app.command("failures")
def test_failures_cli(
    ctx: typer.Context,
    command_id: Annotated[
        str | None,
        typer.Option("--command-id", help="Specific bridge command id to read."),
    ] = None,
    last: Annotated[
        bool,
        typer.Option("--last", help="Read failures from the latest test result artifact."),
    ] = False,
) -> None:
    """Read failure records from a durable test result artifact."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    selected_id = None if last else command_id
    result = read_test_failures_artifact(state.project_root, selected_id)
    print_result(result, state.formatter)


@test_app.command("history")
def test_history_cli(
    ctx: typer.Context,
    max_results: Annotated[
        int,
        typer.Option("--max-results", help="Maximum artifacts to list."),
    ] = 20,
) -> None:
    """List durable test result artifacts newest-first."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = list_test_result_history(state.project_root, max_results=max_results)
    print_result(result, state.formatter)


@test_app.command("progress")
def test_progress_cli(
    ctx: typer.Context,
    command_id: Annotated[
        str | None,
        typer.Option("--command-id", help="Specific bridge command id to read."),
    ] = None,
    last: Annotated[
        bool,
        typer.Option("--last", help="Read the latest test progress artifact."),
    ] = False,
) -> None:
    """Read a durable test progress artifact without contacting Unity."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    selected_id = None if last else command_id
    result = read_test_progress_artifact(state.project_root, selected_id)
    print_result(result, state.formatter)


@test_app.command("events")
def test_events_cli(
    ctx: typer.Context,
    command_id: Annotated[
        str | None,
        typer.Option("--command-id", help="Specific bridge command id to read."),
    ] = None,
    last: Annotated[
        bool,
        typer.Option("--last", help="Read events for the latest test progress artifact."),
    ] = False,
    max_events: Annotated[
        int,
        typer.Option("--max-events", help="Maximum events to return."),
    ] = 100,
) -> None:
    """Read durable test progress events without contacting Unity."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    selected_id = None if last else command_id
    result = read_test_progress_events(
        state.project_root,
        command_id=selected_id,
        max_events=max_events,
    )
    print_result(result, state.formatter)


@test_app.command("rerun-failed")
def test_rerun_failed_cli(
    ctx: typer.Context,
    command_id: Annotated[
        str | None,
        typer.Option("--command-id", help="Specific bridge command id to read."),
    ] = None,
    last: Annotated[
        bool,
        typer.Option("--last", help="Read failures from the latest test result artifact."),
    ] = False,
    platform: Annotated[
        str,
        typer.Option("--platform", "-P", help="Test platform: EditMode or PlayMode."),
    ] = "EditMode",
    timeout: Annotated[
        int,
        typer.Option("--timeout", help="Timeout in seconds."),
    ] = 300,
) -> None:
    """Rerun failed tests from a durable test result artifact."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    selected_id = None if last else command_id
    result = asyncio.run(
        rerun_failed_tests(
            state.bridge,
            state.project_root,
            command_id=selected_id,
            platform=platform,
            timeout=timeout,
        )
    )
    print_result(result, state.formatter)


def _add_selector(
    params: dict[str, object],
    key: str,
    values: list[str] | None,
) -> None:
    if not values:
        return
    cleaned = [value for value in values if value]
    if cleaned:
        params[key] = cleaned


def _enforce_min_tests(result: CommandResult, min_tests: int) -> CommandResult:
    if min_tests <= 0 or not result.success or not isinstance(result.data, dict):
        return result

    total = result.data.get("total")
    if not isinstance(total, int) or total >= min_tests:
        return result

    return CommandResult(
        success=False,
        data=result.data,
        error=f"Expected at least {min_tests} test(s), but Unity reported {total}.",
        command_id=result.command_id,
        execution_time_ms=result.execution_time_ms,
        exit_code=1,
        cached=result.cached,
    )


def _compile_group_patterns(group_names: list[str] | None) -> list[re.Pattern] | CommandResult:
    compiled = []
    for pattern in group_names or []:
        try:
            compiled.append(re.compile(pattern))
        except re.error as exc:
            return CommandResult(
                success=False,
                error=f"Invalid group regex '{pattern}': {exc}",
                exit_code=3,
            )
    return compiled


def _preflight_discovery_failure(discovery: CommandResult) -> CommandResult:
    return CommandResult(
        success=False,
        data={
            "readyToRun": False,
            "checks": [
                {
                    "name": "test_discovery",
                    "success": False,
                    "error": discovery.error,
                }
            ],
        },
        error=f"Test preflight failed during discovery: {discovery.error}",
        command_id=discovery.command_id,
        execution_time_ms=discovery.execution_time_ms,
        exit_code=discovery.exit_code,
        cached=discovery.cached,
    )


def _discovered_tests(data: object) -> list[dict[str, object]]:
    if not isinstance(data, dict):
        return []
    tests = data.get("tests")
    if not isinstance(tests, list):
        return []
    return [test for test in tests if isinstance(test, dict)]


def _select_preflight_tests(
    tests: list[dict[str, object]],
    *,
    test_names: list[str] | None,
    group_patterns: list[re.Pattern],
    categories: list[str] | None,
    assemblies: list[str] | None,
) -> list[dict[str, object]]:
    selected = []
    for test in tests:
        if _matches_preflight_selectors(
            test,
            test_names=test_names,
            group_patterns=group_patterns,
            categories=categories,
            assemblies=assemblies,
        ):
            selected.append(test)
    return selected


def _matches_preflight_selectors(
    test: dict[str, object],
    *,
    test_names: list[str] | None,
    group_patterns: list[re.Pattern],
    categories: list[str] | None,
    assemblies: list[str] | None,
) -> bool:
    full_name = str(test.get("fullName") or "")
    if test_names and full_name not in set(test_names):
        return False
    if group_patterns and not any(pattern.search(full_name) for pattern in group_patterns):
        return False
    if categories and not set(categories).intersection(_test_categories(test)):
        return False
    return not (assemblies and test.get("assembly") not in set(assemblies))


def _test_categories(test: dict[str, object]) -> set[str]:
    value = test.get("categories")
    if isinstance(value, list):
        return {item for item in value if isinstance(item, str)}
    if isinstance(value, str):
        return {item for item in value.split(";") if item}
    return set()


def _preflight_result(
    discovery: CommandResult,
    tests: list[dict[str, object]],
    selected: list[dict[str, object]],
    *,
    platform: str,
    filter_pattern: str | None,
    min_tests: int,
    selectors: dict[str, list[str]],
) -> CommandResult:
    required = max(0, min_tests)
    ready = len(selected) >= required
    payload = _preflight_payload(tests, selected, platform, filter_pattern, required, selectors)
    if ready:
        return CommandResult(
            success=True,
            data=payload,
            command_id=discovery.command_id,
            execution_time_ms=discovery.execution_time_ms,
            cached=discovery.cached,
        )
    return CommandResult(
        success=False,
        data=payload,
        error=f"Test preflight selected {len(selected)} test(s); expected at least {required}.",
        command_id=discovery.command_id,
        execution_time_ms=discovery.execution_time_ms,
        exit_code=1,
        cached=discovery.cached,
    )


def _preflight_payload(
    tests: list[dict[str, object]],
    selected: list[dict[str, object]],
    platform: str,
    filter_pattern: str | None,
    min_tests: int,
    selectors: dict[str, list[str]],
) -> dict[str, object]:
    ready = len(selected) >= min_tests
    return {
        "readyToRun": ready,
        "platform": platform,
        "filter": filter_pattern,
        "selectors": selectors,
        "discoveredCount": len(tests),
        "selectedCount": len(selected),
        "minTests": min_tests,
        "sampleTests": [str(test.get("fullName") or "") for test in selected[:10]],
        "checks": [
            {"name": "test_discovery", "success": True},
            {"name": "min_tests", "success": ready},
        ],
    }


def _failed_test_names(failures: object) -> list[str]:
    if not isinstance(failures, list):
        return []

    names = []
    seen = set()
    for failure in failures:
        if not isinstance(failure, dict):
            continue
        name = failure.get("testName")
        if not isinstance(name, str) or not name or name in seen:
            continue
        names.append(name)
        seen.add(name)
    return names

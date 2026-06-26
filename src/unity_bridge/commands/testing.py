"""Testing commands: test run, compile, test listing.

Async core functions are shared between CLI and MCP entry points.
Typer wrappers provide the CLI surface with ``asyncio.run()``.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Valid list modes
# ---------------------------------------------------------------------------

VALID_LIST_MODES = frozenset({"tests", "categories", "assemblies"})
TEST_RESULTS_RELATIVE_PATH = Path(".claude") / "unity" / "test-results"
TEST_PROGRESS_RELATIVE_PATH = Path(".claude") / "unity" / "test-progress"

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


def read_test_result_artifact(
    project_root: Path,
    command_id: str | None = None,
) -> CommandResult:
    """Read a durable test result artifact from the Unity project."""
    path = _test_result_artifact_path(project_root, command_id)
    if not path.exists():
        name = command_id or "latest"
        return CommandResult(
            success=False,
            error=f"No test result artifact found for '{name}'.",
            exit_code=2,
        )

    try:
        return CommandResult(success=True, data=json.loads(path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        return CommandResult(
            success=False,
            error=f"Invalid test result artifact JSON: {exc}",
            exit_code=5,
        )


def read_test_failures_artifact(
    project_root: Path,
    command_id: str | None = None,
) -> CommandResult:
    """Read failure records from a durable test result artifact."""
    result = read_test_result_artifact(project_root, command_id)
    if not result.success:
        return result

    payload = result.data or {}
    test_result = _artifact_result_payload(payload)
    return CommandResult(
        success=True,
        data={
            "commandId": payload.get("commandId"),
            "writtenAt": payload.get("writtenAt"),
            "failed": test_result.get("failed", 0),
            "failures": test_result.get("failures", []),
        },
    )


def list_test_result_history(project_root: Path, max_results: int = 20) -> CommandResult:
    """List durable test result artifacts newest-first."""
    directory = _test_results_dir(project_root)
    if not directory.exists():
        return CommandResult(success=True, data={"count": 0, "results": []})

    entries = []
    for path in directory.glob("*.json"):
        if path.name == "latest.json":
            continue
        artifact = _load_artifact_for_history(path)
        if artifact is not None:
            entries.append(artifact)

    entries.sort(key=lambda item: item.get("writtenAt") or "", reverse=True)
    limited = entries[: max(0, max_results)]
    return CommandResult(success=True, data={"count": len(limited), "results": limited})


def read_test_progress_artifact(
    project_root: Path,
    command_id: str | None = None,
) -> CommandResult:
    """Read a durable test progress artifact from the Unity project."""
    path = _test_progress_artifact_path(project_root, command_id)
    if not path.exists():
        name = command_id or "latest"
        return CommandResult(
            success=False,
            error=f"No test progress artifact found for '{name}'.",
            exit_code=2,
        )

    try:
        return CommandResult(success=True, data=json.loads(path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        return CommandResult(
            success=False,
            error=f"Invalid test progress artifact JSON: {exc}",
            exit_code=5,
        )


def read_test_progress_events(
    project_root: Path,
    command_id: str | None = None,
    max_events: int = 100,
) -> CommandResult:
    """Read durable JSONL test progress events from the Unity project."""
    selected_id = command_id
    if selected_id is None:
        progress = read_test_progress_artifact(project_root)
        if not progress.success:
            return progress
        selected_id = (progress.data or {}).get("commandId")

    if not isinstance(selected_id, str) or not selected_id:
        return CommandResult(
            success=False,
            error="No test progress command id was available.",
            exit_code=2,
        )

    path = _test_progress_events_path(project_root, selected_id)
    if not path.exists():
        return CommandResult(
            success=False,
            error=f"No test progress event log found for '{selected_id}'.",
            exit_code=2,
        )

    return _read_progress_events_file(path, selected_id, max_events)


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


def _test_results_dir(project_root: Path) -> Path:
    return Path(project_root) / TEST_RESULTS_RELATIVE_PATH


def _test_result_artifact_path(project_root: Path, command_id: str | None) -> Path:
    filename = f"{command_id}.json" if command_id else "latest.json"
    return _test_results_dir(project_root) / filename


def _test_progress_dir(project_root: Path) -> Path:
    return Path(project_root) / TEST_PROGRESS_RELATIVE_PATH


def _test_progress_artifact_path(project_root: Path, command_id: str | None) -> Path:
    filename = f"{command_id}.json" if command_id else "latest.json"
    return _test_progress_dir(project_root) / filename


def _test_progress_events_path(project_root: Path, command_id: str) -> Path:
    return _test_progress_dir(project_root) / f"{command_id}.events.jsonl"


def _artifact_result_payload(payload: dict[str, object]) -> dict:
    result = payload.get("result")
    return result if isinstance(result, dict) else payload


def _load_artifact_for_history(path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None

    result = _artifact_result_payload(payload)
    return {
        "commandId": payload.get("commandId") or path.stem,
        "writtenAt": payload.get("writtenAt"),
        "path": str(path),
        "total": result.get("total", 0),
        "passed": result.get("passed", 0),
        "failed": result.get("failed", 0),
        "skipped": result.get("skipped", 0),
        "inconclusive": result.get("inconclusive", 0),
    }


def _read_progress_events_file(path: Path, command_id: str, max_events: int) -> CommandResult:
    events = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as exc:
            return CommandResult(
                success=False,
                error=f"Invalid test progress event JSON on line {line_number}: {exc}",
                exit_code=5,
            )
        if len(events) >= max(0, max_events):
            break
    return CommandResult(
        success=True,
        data={
            "commandId": command_id,
            "path": str(path),
            "count": len(events),
            "events": events,
        },
    )


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

"""Durable Unity Test Runner artifact readers."""

from __future__ import annotations

import json
from pathlib import Path

from unity_bridge.core.bridge import CommandResult

TEST_RESULTS_RELATIVE_PATH = Path(".claude") / "unity" / "test-results"
TEST_PROGRESS_RELATIVE_PATH = Path(".claude") / "unity" / "test-progress"


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

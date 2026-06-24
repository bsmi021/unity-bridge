"""Unit tests for Python-side queued Unity command dispatch."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from unity_bridge.core.bridge import CommandResult, DirectBridge
from unity_bridge.core.command_queue import CommandQueue, _result_status
from unity_bridge.core.operation import STATE_ABANDONED, STATE_QUEUED, OperationStore


def test_submit_persists_queued_operation_without_command_file(fake_project: Path) -> None:
    bridge = DirectBridge(fake_project)
    queue = CommandQueue(fake_project, bridge=bridge, auto_start=False)

    result = queue.submit(
        "set-component-data",
        {"gameObjectPath": "Player", "componentType": "Mover"},
        timeout=10.0,
    )

    command_id = result.command_id
    assert command_id is not None
    record = OperationStore(fake_project).load(command_id)
    assert result.success is True
    assert result.data["status"] == STATE_QUEUED
    assert result.data["commandId"] == command_id
    assert record is not None
    assert record.state == STATE_QUEUED
    assert not Path(record.command_path).exists()


async def test_dispatch_uses_queued_command_id(fake_project: Path) -> None:
    bridge = DirectBridge(fake_project)
    bridge.send_prepared_command = AsyncMock(  # type: ignore[attr-defined]
        return_value=CommandResult(success=True, command_id="placeholder")
    )
    queue = CommandQueue(fake_project, bridge=bridge, auto_start=False)
    result = queue.submit("query-hierarchy", {"maxDepth": 1}, timeout=5.0)

    dispatch_result = await queue.dispatch(result.command_id)

    assert dispatch_result.success is True
    bridge.send_prepared_command.assert_awaited_once_with(
        command_id=result.command_id,
        command_type="query-hierarchy",
        parameters={"maxDepth": 1},
        timeout=5.0,
        check_health=True,
        create_operation=False,
    )


async def test_dispatch_readiness_timeout_abandons_queued_operation(fake_project: Path) -> None:
    bridge = DirectBridge(fake_project)
    bridge.send_prepared_command = AsyncMock(  # type: ignore[attr-defined]
        return_value=CommandResult(
            success=False,
            error="Unity Editor is busy compiling; command was not sent",
            command_id="placeholder",
            data={"status": "editor_busy", "retryable": True},
            exit_code=4,
        )
    )
    queue = CommandQueue(fake_project, bridge=bridge, auto_start=False)
    result = queue.submit("set-component-data", {"field": "value"}, timeout=5.0)

    await queue.dispatch(result.command_id)

    record = OperationStore(fake_project).load(result.command_id)
    assert record is not None
    assert record.state == STATE_ABANDONED
    assert "busy compiling" in record.last_error
    assert not queue._queue_file(result.command_id).exists()


async def test_dispatch_requires_command_id(fake_project: Path) -> None:
    queue = CommandQueue(fake_project, auto_start=False)

    result = await queue.dispatch(None)

    assert result.success is False
    assert result.data["status"] == "not_found"
    assert result.error == "Missing command ID"
    assert result.exit_code == 2


async def test_dispatch_missing_queue_file_returns_not_found(fake_project: Path) -> None:
    queue = CommandQueue(fake_project, auto_start=False)

    result = await queue.dispatch("missing-command")

    assert result.success is False
    assert result.command_id == "missing-command"
    assert result.data == {"commandId": "missing-command", "status": "not_found"}
    assert "Queued command not found" in result.error
    assert result.exit_code == 2


async def test_dispatch_unreadable_queue_file_returns_not_found(
    fake_project: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    queue = CommandQueue(fake_project, auto_start=False)
    queue._queue_file("corrupt-command").write_text("{", encoding="utf-8")

    with caplog.at_level("WARNING", logger="unity_bridge.command_queue"):
        result = await queue.dispatch("corrupt-command")

    assert result.success is False
    assert result.command_id == "corrupt-command"
    assert result.data["status"] == "not_found"
    assert "Queued command corrupt-command is unreadable" in caplog.text


def test_write_queue_file_cleans_temp_file_on_replace_failure(fake_project: Path) -> None:
    queue = CommandQueue(fake_project, auto_start=False)
    queued = queue._create_queued_command("query-hierarchy", {}, 5.0)

    with patch.object(Path, "replace", side_effect=PermissionError("locked")):
        with pytest.raises(PermissionError, match="locked"):
            queue._write_queue_file(queued)

    assert not any(queue.queue_path.glob("*.tmp"))
    assert not queue._queue_file(queued.command_id).exists()


def test_start_dispatch_returns_false_without_running_loop(fake_project: Path) -> None:
    queue = CommandQueue(fake_project, auto_start=False)
    queue.dispatch = AsyncMock(return_value=CommandResult(success=True))  # type: ignore[method-assign]

    assert queue._start_dispatch("command-id") is False

    queue.dispatch.assert_not_called()


async def test_start_dispatch_tracks_and_finishes_background_task(fake_project: Path) -> None:
    queue = CommandQueue(fake_project, auto_start=False)
    queue.dispatch = AsyncMock(return_value=CommandResult(success=True))  # type: ignore[method-assign]

    assert queue._start_dispatch("command-id") is True
    task = queue._tasks["command-id"]
    await task
    await asyncio.sleep(0)

    queue.dispatch.assert_awaited_once_with("command-id")
    assert "command-id" not in queue._tasks


def test_finish_task_logs_background_exception(
    fake_project: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    queue = CommandQueue(fake_project, auto_start=False)
    task = MagicMock()
    task.result.side_effect = RuntimeError("boom")
    queue._tasks["command-id"] = task

    with caplog.at_level("WARNING", logger="unity_bridge.command_queue"):
        queue._finish_task("command-id", task)  # type: ignore[arg-type]

    assert "command-id" not in queue._tasks
    assert "Queued command command-id dispatch failed: boom" in caplog.text


def test_result_status_returns_none_for_non_dict_data() -> None:
    result = CommandResult(success=True, data=["editor_busy"])

    assert _result_status(result) is None

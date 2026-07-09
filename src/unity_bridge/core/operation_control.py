"""CLI control-plane helpers for detached bridge operations."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any

from unity_bridge.core.bridge import CommandResult, DirectBridge
from unity_bridge.core.command_queue import CommandQueue, QueuedCommand
from unity_bridge.core.operation import (
    STATE_ABANDONED,
    STATE_COMPLETED,
    STATE_FAILED,
    STATE_INTERRUPTED,
    STATE_QUEUED,
    OperationRecord,
    OperationStore,
)

_COMMAND_TYPE_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def submit_operation(
    project_root: Path,
    command_type: str,
    parameters: dict[str, Any] | None = None,
    *,
    timeout: float = 30.0,
    client_policy: dict[str, Any] | None = None,
) -> CommandResult:
    """Queue an operation without contacting Unity."""
    if not _COMMAND_TYPE_RE.fullmatch(command_type):
        return CommandResult(
            success=False,
            error=f"Invalid command type: {command_type}",
            exit_code=3,
        )
    queue = CommandQueue(project_root, auto_start=False)
    return queue.submit(command_type, parameters or {}, timeout, client_policy=client_policy)


async def wait_operation(
    project_root: Path,
    command_id: str,
    *,
    timeout: float = 30.0,
    poll_interval: float = 0.5,
) -> CommandResult:
    """Dispatch and poll a durable operation until terminal or caller patience expires."""
    bridge = DirectBridge(project_root)
    queue = CommandQueue(project_root, bridge=bridge, auto_start=False)
    store = OperationStore(project_root)
    start = asyncio.get_running_loop().time()
    interval = max(0.001, poll_interval)

    while True:
        elapsed = asyncio.get_running_loop().time() - start
        response = await _read_response_if_present(bridge, store, command_id, elapsed)
        if response is not None:
            return _finish_response(queue, command_id, response)

        record = store.load(command_id)
        if record is None:
            if _command_file_exists(bridge, command_id):
                if elapsed >= timeout:
                    return _orphan_in_flight_timeout(command_id)
                await asyncio.sleep(interval)
                continue
            return _not_found(command_id)
        terminal = _terminal_result(queue, record)
        if terminal is not None:
            return terminal
        dispatch = await _dispatch_if_queued(
            queue,
            record,
            readiness_timeout=_readiness_budget(timeout - elapsed, interval),
        )
        if dispatch is not None and not dispatch.success:
            return dispatch
        if elapsed >= timeout:
            return _wait_timeout(record)
        await asyncio.sleep(interval)


async def _read_response_if_present(
    bridge: DirectBridge,
    store: OperationStore,
    command_id: str,
    elapsed: float,
) -> CommandResult | None:
    record = store.load(command_id)
    for response_path in _response_candidates(bridge, record, command_id):
        if response_path.exists():
            return await bridge.read_terminal_response(response_path, command_id, elapsed)
    return None


async def _dispatch_if_queued(
    queue: CommandQueue,
    record: OperationRecord,
    *,
    readiness_timeout: float,
) -> CommandResult | None:
    if record.state != STATE_QUEUED:
        return None
    queued = queue._load_queue_file(record.command_id)
    if queued is None:
        if _operation_file_exists(record):
            return None
        return _stale_queue(record)
    return await queue.dispatch(record.command_id, readiness_timeout=readiness_timeout)


def _finish_response(
    queue: CommandQueue,
    command_id: str,
    result: CommandResult,
) -> CommandResult:
    queued = queue._load_queue_file(command_id)
    queue.remove_metadata(command_id)
    if result.success and queued is not None:
        return _apply_client_policy(result, queued)
    return result


def _apply_client_policy(result: CommandResult, queued: QueuedCommand) -> CommandResult:
    policy = queued.client_policy or {}
    min_tests = int(policy.get("minTests") or 0)
    if min_tests <= 0 or not isinstance(result.data, dict):
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


def _terminal_result(queue: CommandQueue, record: OperationRecord) -> CommandResult | None:
    if record.state not in {STATE_COMPLETED, STATE_FAILED, STATE_INTERRUPTED, STATE_ABANDONED}:
        return None
    queue.remove_metadata(record.command_id)
    if record.state == STATE_COMPLETED:
        return CommandResult(success=True, data=record.to_dict(), command_id=record.command_id)
    return CommandResult(
        success=False,
        data=record.to_dict(),
        error=record.last_error or f"Operation ended in {record.state}",
        command_id=record.command_id,
        exit_code=1,
    )


def _wait_timeout(record: OperationRecord) -> CommandResult:
    return CommandResult(
        success=True,
        data={
            "commandId": record.command_id,
            "status": record.state,
            "retryable": True,
            "waitTimedOut": True,
            "operation": record.to_dict(),
        },
        command_id=record.command_id,
    )


def _stale_queue(record: OperationRecord) -> CommandResult:
    return CommandResult(
        success=False,
        data={"commandId": record.command_id, "status": "stale_queue"},
        error=f"Queued operation has no queue metadata: {record.command_id}",
        command_id=record.command_id,
        exit_code=2,
    )


def _not_found(command_id: str) -> CommandResult:
    return CommandResult(
        success=False,
        data={"commandId": command_id, "status": "not_found"},
        error=f"Operation not found: {command_id}",
        command_id=command_id,
        exit_code=2,
    )


def _orphan_in_flight_timeout(command_id: str) -> CommandResult:
    return CommandResult(
        success=True,
        data={
            "commandId": command_id,
            "status": "in_flight",
            "retryable": True,
            "waitTimedOut": True,
        },
        command_id=command_id,
    )


def _operation_file_exists(record: OperationRecord) -> bool:
    return any(
        Path(path).exists()
        for path in (record.command_path, record.response_path)
        if path
    )


def _response_candidates(
    bridge: DirectBridge,
    record: OperationRecord | None,
    command_id: str,
) -> list[Path]:
    candidates: list[Path] = []
    if record is not None and record.response_path:
        candidates.append(Path(record.response_path))
    candidates.extend(sorted(bridge.responses_path.glob(f"{command_id}-*.json")))
    return list(dict.fromkeys(candidates))


def _command_file_exists(bridge: DirectBridge, command_id: str) -> bool:
    return any(bridge.commands_path.glob(f"{command_id}-*.json"))


def _readiness_budget(remaining: float, poll_interval: float) -> float:
    return max(0.001, min(max(remaining, 0.001), poll_interval))

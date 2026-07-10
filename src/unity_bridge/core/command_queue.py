"""Python-side queue for Unity commands waiting on editor readiness."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from unity_bridge.core.bridge import CommandResult, DirectBridge
from unity_bridge.core.operation import (
    STATE_ACCEPTED,
    STATE_COMPLETED,
    STATE_FAILED,
    STATE_INTERRUPTED,
    STATE_QUEUED,
    STATE_RECOVERING,
    STATE_RUNNING,
    OperationStore,
    retry_policy_for_command,
)

logger = logging.getLogger("unity_bridge.command_queue")
_DISPATCH_LOCK_STALE_SECONDS = 60.0


@dataclass(frozen=True)
class QueuedCommand:
    """Command payload held outside Unity's command directory until ready."""

    command_id: str
    command_type: str
    parameters: dict[str, Any]
    timeout: float
    dispatch_state: str = STATE_QUEUED
    attempt_count: int = 0
    last_attempt_at: str | None = None
    last_deferred_reason: str | None = None
    client_policy: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the queue payload shape."""
        return {
            "commandId": self.command_id,
            "commandType": self.command_type,
            "parameters": self.parameters,
            "timeout": self.timeout,
            "dispatchState": self.dispatch_state,
            "attemptCount": self.attempt_count,
            "lastAttemptAt": self.last_attempt_at,
            "lastDeferredReason": self.last_deferred_reason,
            "clientPolicy": self.client_policy,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QueuedCommand:
        """Deserialize from a queue payload file."""
        return cls(
            command_id=str(data["commandId"]),
            command_type=str(data["commandType"]),
            parameters=dict(data.get("parameters") or {}),
            timeout=float(data.get("timeout", 30.0)),
            dispatch_state=str(data.get("dispatchState") or STATE_QUEUED),
            attempt_count=int(data.get("attemptCount") or 0),
            last_attempt_at=data.get("lastAttemptAt"),
            last_deferred_reason=data.get("lastDeferredReason"),
            client_policy=(
                dict(data["clientPolicy"]) if isinstance(data.get("clientPolicy"), dict) else None
            ),
        )


class CommandQueue:
    """Accept commands immediately and dispatch them when Unity is ready."""

    def __init__(
        self,
        project_root: Path,
        *,
        bridge: DirectBridge | None = None,
        auto_start: bool = True,
    ) -> None:
        self.project_root = Path(project_root)
        self.bridge = bridge or DirectBridge(self.project_root)
        self.auto_start = auto_start
        self.queue_path = self.project_root / ".claude" / "unity" / "queue"
        self.queue_path.mkdir(parents=True, exist_ok=True)
        self._operation_store = OperationStore(self.project_root)
        self._tasks: dict[str, asyncio.Task[CommandResult]] = {}

    def submit(
        self,
        command_type: str,
        parameters: dict[str, Any] | None = None,
        timeout: float = 30.0,
        client_policy: dict[str, Any] | None = None,
    ) -> CommandResult:
        """Queue a Unity command and optionally start background dispatch."""
        queued = self._create_queued_command(command_type, parameters or {}, timeout, client_policy)
        self._write_queue_file(queued)
        try:
            self._create_operation_record(queued)
        except OSError as exc:
            self.remove_metadata(queued.command_id)
            return CommandResult(
                success=False,
                error=f"Could not persist detached operation: {exc}",
                command_id=queued.command_id,
                exit_code=1,
            )
        dispatch_started = self._start_dispatch(queued.command_id) if self.auto_start else False
        return CommandResult(
            success=True,
            data={
                "status": STATE_QUEUED,
                "commandId": queued.command_id,
                "commandType": queued.command_type,
                "waitCommand": f"unity-bridge operation wait {queued.command_id}",
                "dispatchStarted": dispatch_started,
            },
            command_id=queued.command_id,
        )

    async def dispatch(
        self,
        command_id: str | None,
        *,
        readiness_timeout: float | None = None,
    ) -> CommandResult:
        """Dispatch a queued command through DirectBridge."""
        if not command_id:
            return CommandResult(
                success=False,
                data={"status": "not_found"},
                error="Missing command ID",
                exit_code=2,
            )
        queued = self._load_queue_file(command_id)
        if queued is None:
            return CommandResult(
                success=False,
                data={"commandId": command_id, "status": "not_found"},
                error=f"Queued command not found: {command_id}",
                command_id=command_id,
                exit_code=2,
            )

        existing = self._existing_dispatch_result(queued)
        if existing is not None:
            return existing

        if not self._acquire_dispatch_lock(queued):
            return CommandResult(
                success=True,
                data={
                    "commandId": queued.command_id,
                    "status": STATE_QUEUED,
                    "dispatchDeferred": True,
                    "reason": "Dispatch already in progress",
                },
                command_id=queued.command_id,
            )

        queued = self._record_dispatch_attempt(queued)
        try:
            result = await self.bridge.dispatch_prepared_command(
                command_id=queued.command_id,
                command_type=queued.command_type,
                parameters=queued.parameters,
                timeout=queued.timeout,
                check_health=True,
                create_operation=False,
                readiness_timeout=readiness_timeout,
            )
        finally:
            self._release_dispatch_lock(queued.command_id)
        result.command_id = queued.command_id
        return self._finish_dispatch(queued, result)

    def is_queued(self, command_id: str) -> bool:
        """Whether queue metadata exists for the command."""
        return self._queue_file(command_id).exists()

    def remove_metadata(self, command_id: str) -> None:
        """Remove queue metadata and dispatch lock for a terminal operation."""
        self._queue_file(command_id).unlink(missing_ok=True)
        self._lock_file(command_id).unlink(missing_ok=True)

    def command_file_exists(self, queued: QueuedCommand) -> bool:
        """Whether this queued command already has a command file on disk."""
        record = self._operation_store.load(queued.command_id)
        if record is not None and record.command_path:
            return Path(record.command_path).exists()
        path = self.bridge.commands_path / f"{queued.command_id}-{queued.command_type}.json"
        return path.exists()

    def _existing_dispatch_result(self, queued: QueuedCommand) -> CommandResult | None:
        record = self._operation_store.load(queued.command_id)
        if record is not None and record.state in {
            STATE_ACCEPTED,
            STATE_RUNNING,
            STATE_RECOVERING,
            STATE_COMPLETED,
            STATE_FAILED,
            STATE_INTERRUPTED,
        }:
            return CommandResult(
                success=True,
                data={"commandId": queued.command_id, "status": record.state},
                command_id=queued.command_id,
            )
        if self.command_file_exists(queued):
            updated = self._replace_metadata(queued, dispatch_state="dispatched")
            return CommandResult(
                success=True,
                data={"commandId": updated.command_id, "status": "dispatched"},
                command_id=updated.command_id,
            )
        return None

    def _record_dispatch_attempt(self, queued: QueuedCommand) -> QueuedCommand:
        return self._replace_metadata(
            queued,
            dispatch_state="dispatching",
            attempt_count=queued.attempt_count + 1,
            last_attempt_at=_utc_now(),
        )

    def _replace_metadata(self, queued: QueuedCommand, **changes: Any) -> QueuedCommand:
        updated = QueuedCommand(
            command_id=queued.command_id,
            command_type=queued.command_type,
            parameters=queued.parameters,
            timeout=queued.timeout,
            dispatch_state=changes.get("dispatch_state", queued.dispatch_state),
            attempt_count=changes.get("attempt_count", queued.attempt_count),
            last_attempt_at=changes.get("last_attempt_at", queued.last_attempt_at),
            last_deferred_reason=changes.get(
                "last_deferred_reason",
                queued.last_deferred_reason,
            ),
            client_policy=changes.get("client_policy", queued.client_policy),
        )
        self._write_queue_file(updated)
        return updated

    def _defer_dispatch(self, queued: QueuedCommand, result: CommandResult) -> CommandResult:
        reason = result.error or "Editor readiness timed out before dispatch"
        updated = self._replace_metadata(
            queued,
            dispatch_state=STATE_QUEUED,
            last_deferred_reason=reason,
        )
        self._operation_store.transition(
            queued.command_id,
            STATE_QUEUED,
            reason=reason,
            busy_reason=reason,
        )
        return CommandResult(
            success=True,
            data={
                "commandId": updated.command_id,
                "status": STATE_QUEUED,
                "retryable": True,
                "dispatchDeferred": True,
                "reason": reason,
            },
            command_id=updated.command_id,
        )

    def _lock_file(self, command_id: str) -> Path:
        return self.queue_path / f"{command_id}.lock"

    def _acquire_dispatch_lock(self, queued: QueuedCommand) -> bool:
        lock = self._lock_file(queued.command_id)
        if lock.exists() and not self.command_file_exists(queued):
            self._remove_stale_lock(lock)
        if lock.exists() and not self.command_file_exists(queued):
            return False
        try:
            with lock.open("x", encoding="utf-8") as handle:
                handle.write(_utc_now())
            return True
        except FileExistsError:
            return False

    def _release_dispatch_lock(self, command_id: str) -> None:
        self._lock_file(command_id).unlink(missing_ok=True)

    def _remove_stale_lock(self, lock: Path) -> None:
        try:
            age = time.time() - lock.stat().st_mtime
        except OSError:
            return
        if age >= _DISPATCH_LOCK_STALE_SECONDS:
            lock.unlink(missing_ok=True)

    async def dispatch_and_wait(self, queued: QueuedCommand) -> CommandResult:
        """Compatibility helper for callers that need the old wait behavior."""
        return await self.bridge.send_prepared_command(
            command_id=queued.command_id,
            command_type=queued.command_type,
            parameters=queued.parameters,
            timeout=queued.timeout,
            check_health=True,
            create_operation=False,
        )

    def _create_queued_command(
        self,
        command_type: str,
        parameters: dict[str, Any],
        timeout: float,
        client_policy: dict[str, Any] | None = None,
    ) -> QueuedCommand:
        return QueuedCommand(
            command_id=str(uuid.uuid4()),
            command_type=command_type,
            parameters=parameters,
            timeout=float(timeout),
            client_policy=client_policy,
        )

    def _create_operation_record(self, queued: QueuedCommand) -> None:
        self._operation_store.create_queued(
            command_id=queued.command_id,
            command_type=queued.command_type,
            parameters=queued.parameters,
            command_path=self.bridge.commands_path
            / f"{queued.command_id}-{queued.command_type}.json",
            response_path=self.bridge.responses_path
            / f"{queued.command_id}-{queued.command_type}.json",
            domain_generation=None,
            retry_policy=retry_policy_for_command(queued.command_type),
            idempotency_key=queued.parameters.get("idempotencyKey"),
        )

    def _queue_file(self, command_id: str) -> Path:
        return self.queue_path / f"{command_id}.json"

    def _write_queue_file(self, queued: QueuedCommand) -> None:
        path = self._queue_file(queued.command_id)
        temp = path.with_suffix(f".{uuid.uuid4().hex}.tmp")
        try:
            temp.write_text(json.dumps(queued.to_dict(), indent=2), encoding="utf-8")
            temp.replace(path)
        except BaseException:
            temp.unlink(missing_ok=True)
            raise

    def _load_queue_file(self, command_id: str) -> QueuedCommand | None:
        path = self._queue_file(command_id)
        if not path.exists():
            return None
        try:
            return QueuedCommand.from_dict(json.loads(path.read_text(encoding="utf-8-sig")))
        except (json.JSONDecodeError, KeyError, OSError, TypeError, ValueError) as exc:
            logger.warning("Queued command %s is unreadable: %s", command_id, exc)
            return None

    def _start_dispatch(self, command_id: str) -> bool:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return False
        task = loop.create_task(self.dispatch(command_id))
        self._tasks[command_id] = task
        task.add_done_callback(lambda done: self._finish_task(command_id, done))
        return True

    def _finish_task(self, command_id: str, task: asyncio.Task[CommandResult]) -> None:
        self._tasks.pop(command_id, None)
        try:
            task.result()
        except Exception as exc:
            logger.warning("Queued command %s dispatch failed: %s", command_id, exc)

    def _finish_dispatch(self, queued: QueuedCommand, result: CommandResult) -> CommandResult:
        if not result.success and _result_status(result) == "editor_busy":
            return self._defer_dispatch(queued, result)
        if result.success:
            self._replace_metadata(queued, dispatch_state="dispatched")
        return result


def _result_status(result: CommandResult) -> str | None:
    if isinstance(result.data, dict):
        status = result.data.get("status")
        return str(status) if status is not None else None
    return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

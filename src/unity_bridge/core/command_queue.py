"""Python-side queue for Unity commands waiting on editor readiness."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from unity_bridge.core.bridge import CommandResult, DirectBridge
from unity_bridge.core.operation import (
    STATE_ABANDONED,
    STATE_QUEUED,
    OperationStore,
    retry_policy_for_command,
)

logger = logging.getLogger("unity_bridge.command_queue")


@dataclass(frozen=True)
class QueuedCommand:
    """Command payload held outside Unity's command directory until ready."""

    command_id: str
    command_type: str
    parameters: dict[str, Any]
    timeout: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the queue payload shape."""
        return {
            "commandId": self.command_id,
            "commandType": self.command_type,
            "parameters": self.parameters,
            "timeout": self.timeout,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QueuedCommand:
        """Deserialize from a queue payload file."""
        return cls(
            command_id=str(data["commandId"]),
            command_type=str(data["commandType"]),
            parameters=dict(data.get("parameters") or {}),
            timeout=float(data.get("timeout", 30.0)),
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
    ) -> CommandResult:
        """Queue a Unity command and optionally start background dispatch."""
        queued = self._create_queued_command(command_type, parameters or {}, timeout)
        self._write_queue_file(queued)
        self._create_operation_record(queued)
        dispatch_started = self._start_dispatch(queued.command_id) if self.auto_start else False
        return CommandResult(
            success=True,
            data={
                "status": STATE_QUEUED,
                "commandId": queued.command_id,
                "commandType": queued.command_type,
                "dispatchStarted": dispatch_started,
            },
            command_id=queued.command_id,
        )

    async def dispatch(self, command_id: str | None) -> CommandResult:
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

        result = await self.bridge.send_prepared_command(
            command_id=queued.command_id,
            command_type=queued.command_type,
            parameters=queued.parameters,
            timeout=queued.timeout,
            check_health=True,
            create_operation=False,
        )
        result.command_id = queued.command_id
        self._finish_dispatch(queued, result)
        return result

    def _create_queued_command(
        self,
        command_type: str,
        parameters: dict[str, Any],
        timeout: float,
    ) -> QueuedCommand:
        return QueuedCommand(
            command_id=str(uuid.uuid4()),
            command_type=command_type,
            parameters=parameters,
            timeout=float(timeout),
        )

    def _create_operation_record(self, queued: QueuedCommand) -> None:
        self._operation_store.create_queued(
            command_id=queued.command_id,
            command_type=queued.command_type,
            parameters=queued.parameters,
            command_path=self.bridge.commands_path / f"{queued.command_id}-{queued.command_type}.json",
            response_path=self.bridge.responses_path / f"{queued.command_id}-{queued.command_type}.json",
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

    def _finish_dispatch(self, queued: QueuedCommand, result: CommandResult) -> None:
        if not result.success and _result_status(result) == "editor_busy":
            self._operation_store.transition(
                queued.command_id,
                STATE_ABANDONED,
                reason=result.error or "Editor readiness timed out before dispatch",
            )
        self._queue_file(queued.command_id).unlink(missing_ok=True)


def _result_status(result: CommandResult) -> str | None:
    if isinstance(result.data, dict):
        status = result.data.get("status")
        return str(status) if status is not None else None
    return None

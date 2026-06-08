"""
DirectBridge — async file-based communication with Unity Editor.

Migrated from direct_bridge.py. Provides the core command dispatch layer
that writes command JSON files and polls for response files.

All commands return CommandResult dataclass instead of raw dicts.
"""

import asyncio
import json
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiofiles

from unity_bridge.core.operation import (
    STATE_ABANDONED,
    STATE_ACCEPTED,
    STATE_COMPLETED,
    STATE_FAILED,
    STATE_INTERRUPTED,
    STATE_RUNNING,
    STATE_RECOVERING,
    OperationStore,
    retry_policy_for_command,
    terminal_state_for_response_status,
)

logger = logging.getLogger("unity_bridge.bridge")


@dataclass
class CommandResult:
    """Standardized result from any bridge command.

    This is the canonical result type used by both CLI and MCP entry points.
    All command functions return this instead of raw dicts.

    Attributes:
        success: Whether the command completed successfully.
        data: Response payload from Unity (parsed JSON or None).
        error: Human-readable error message if failed.
        command_id: Unique UUID for this command invocation.
        execution_time_ms: Wall-clock time in milliseconds.
        exit_code: Process exit code (0=success, 1=error, 2=not-found).
        cached: Whether this result was served from cache.
    """

    success: bool
    data: Any | None = None
    error: str | None = None
    command_id: str | None = None
    execution_time_ms: int = 0
    exit_code: int = 0
    cached: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "command_id": self.command_id,
            "execution_time_ms": self.execution_time_ms,
            "exit_code": self.exit_code,
            "cached": self.cached,
        }


class DirectBridge:
    """Direct communication with Unity Bridge via file system.

    Writes command JSON to .claude/unity/commands/ and polls
    .claude/unity/responses/ for the response file.

    Attributes:
        project_root: Path to Unity project root (contains Assets/).
        commands_path: Path to .claude/unity/commands directory.
        responses_path: Path to .claude/unity/responses directory.
    """

    DEFAULT_POLL_INTERVAL: float = 0.05  # 50ms
    MIN_RESPONSE_DELAY: float = 0.02  # 20ms
    DEFAULT_EDITOR_READY_TIMEOUT: float = 180.0
    EDITOR_READY_POLL_INTERVAL: float = 0.5
    DEFAULT_IN_FLIGHT_BUSY_GRACE: float = 300.0

    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root)
        self.commands_path = self.project_root / ".claude" / "unity" / "commands"
        self.responses_path = self.project_root / ".claude" / "unity" / "responses"
        self._operation_store = OperationStore(self.project_root)

        self._health_monitor = None
        try:
            from unity_bridge.core.health import HealthMonitor

            self._health_monitor = HealthMonitor(self.project_root)
        except ImportError:
            logger.warning("HealthMonitor not available — health checks disabled.")

        self.commands_path.mkdir(parents=True, exist_ok=True)
        self.responses_path.mkdir(parents=True, exist_ok=True)
        logger.debug("DirectBridge initialized for project: %s", project_root)

    async def send_command(
        self,
        command_type: str,
        parameters: dict[str, Any] | None = None,
        timeout: float = 30.0,
        check_health: bool = True,
    ) -> CommandResult:
        """Send a command to Unity and wait for the response.

        Args:
            command_type: Bridge command type (e.g. "run-tests").
            parameters: Command parameters dict.
            timeout: Max seconds to wait for a response.
            check_health: Whether to check heartbeat before sending.

        Returns:
            CommandResult with success/error and parsed data.
        """
        health = None
        if check_health and self._health_monitor:
            health = self._wait_for_editor_ready()
            if not health.ready:
                return self._readiness_failure(health)

        command_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        command = {
            "commandId": command_id,
            "commandType": command_type,
            "timestamp": timestamp,
            "parametersJson": json.dumps(parameters or {}),
        }

        command_file = self.commands_path / f"{command_id}-{command_type}.json"
        response_file = self.responses_path / f"{command_id}-{command_type}.json"
        self._operation_store.create_queued(
            command_id=command_id,
            command_type=command_type,
            parameters=parameters,
            command_path=command_file,
            response_path=response_file,
            domain_generation=getattr(health, "domain_generation", None),
            retry_policy=retry_policy_for_command(command_type),
            idempotency_key=(parameters or {}).get("idempotencyKey"),
        )

        try:
            await self._write_command_file(command, command_file)
            logger.debug("Sent command: %s (ID: %s)", command_type, command_id)
            return await self._wait_for_response(response_file, command_file, command_id, timeout)
        except Exception as exc:
            logger.error("Error sending command: %s", exc)
            command_file.unlink(missing_ok=True)
            self._operation_store.transition(command_id, STATE_ABANDONED, reason=str(exc))
            return CommandResult(
                success=False,
                error=f"Failed to send command: {exc}",
                command_id=command_id,
                exit_code=1,
            )

    async def send_command_with_retry(
        self,
        command_type: str,
        parameters: dict[str, Any] | None = None,
        timeout: float = 30.0,
        retry_config: Any | None = None,
    ) -> CommandResult:
        """Send command with automatic retry on transient failures.

        Args:
            command_type: Bridge command type.
            parameters: Command parameters dict.
            timeout: Timeout per attempt in seconds.
            retry_config: RetryConfig instance (uses default if None).

        Returns:
            CommandResult from the successful (or final) attempt.
        """
        try:
            from unity_bridge.core.retry import retry_async
        except ImportError:
            logger.warning("retry module not available — retries disabled.")
            return await self.send_command(command_type, parameters, timeout)

        async def attempt() -> CommandResult:
            return await self.send_command(command_type, parameters, timeout)

        return await retry_async(attempt, config=retry_config)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _write_command_file(self, command: dict[str, Any], command_file: Path) -> None:
        """Write command JSON atomically via temp file + rename."""
        temp_file = command_file.with_suffix(".json.tmp")
        async with aiofiles.open(temp_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(command))
        try:
            temp_file.replace(command_file)
        except OSError:
            if command_file.exists():
                command_file.unlink()
            temp_file.rename(command_file)

    async def _wait_for_response(
        self,
        response_file: Path,
        command_file: Path,
        command_id: str,
        timeout: float,
    ) -> CommandResult:
        """Poll for the response file until it appears or timeout."""
        start = asyncio.get_running_loop().time()
        busy_started: float | None = None
        busy_elapsed = 0.0
        origin_generation = self._operation_domain_generation(command_id)
        await asyncio.sleep(self.MIN_RESPONSE_DELAY)

        while True:
            now = asyncio.get_running_loop().time()
            elapsed = now - start
            status = self._current_in_flight_health()
            busy_started, busy_elapsed = self._update_busy_accounting(
                status,
                now,
                busy_started,
                busy_elapsed,
            )
            current_busy_elapsed = (now - busy_started) if busy_started is not None else 0.0
            active_elapsed = elapsed - busy_elapsed - current_busy_elapsed
            if self._domain_generation_changed(status, origin_generation):
                self._mark_recovering_after_reload(
                    command_id,
                    getattr(status, "busy_reason", None),
                )
            if active_elapsed > timeout:
                return self._response_timeout_result(
                    command_file,
                    command_id,
                    elapsed,
                    timeout,
                    status,
                )
            if elapsed > timeout + _in_flight_busy_grace():
                return self._busy_timeout_result(command_id, elapsed, status)

            if response_file.exists():
                result = await self._try_read_response(response_file, command_id, elapsed)
                if result is not None:
                    return result

            await asyncio.sleep(self.DEFAULT_POLL_INTERVAL)

    async def _try_read_response(
        self, response_file: Path, command_id: str, elapsed: float
    ) -> CommandResult | None:
        """Attempt to read and parse the response file.

        Returns None if the file is not ready (mid-write, still running).
        """
        await asyncio.sleep(0.01)  # brief delay for write completion
        try:
            async with aiofiles.open(response_file, "r", encoding="utf-8") as f:
                content = await f.read()
            response = json.loads(content)
        except (json.JSONDecodeError, IOError) as exc:
            logger.warning("Response read failed (will retry): %s", exc)
            return None

        status = response.get("status", "unknown")
        if status == "running":
            logger.debug("Command %s still running...", command_id)
            record = self._operation_store.load(command_id)
            if record is not None and record.state != STATE_RUNNING:
                self._operation_store.transition(
                    command_id, STATE_RUNNING, reason="Unity reported running"
                )
            return None

        response_file.unlink(missing_ok=True)
        terminal_state = terminal_state_for_response_status(status)
        if terminal_state is not None:
            self._operation_store.transition(command_id, terminal_state, reason=status)

        if status == "success":
            data = self._parse_data_json(response)
            return CommandResult(
                success=True,
                data=data,
                command_id=command_id,
                execution_time_ms=int(elapsed * 1000),
            )

        return CommandResult(
            success=False,
            error=response.get("errorMessage", "Unknown error"),
            command_id=command_id,
            execution_time_ms=int(elapsed * 1000),
            exit_code=1,
        )

    def _current_in_flight_health(self) -> Any | None:
        """Read heartbeat during a response wait, if health is available."""
        if not self._health_monitor:
            return None
        try:
            return self._health_monitor.check_health()
        except Exception as exc:
            logger.debug("In-flight health check failed: %s", exc)
            return None

    @staticmethod
    def _update_busy_accounting(
        health: Any | None,
        now: float,
        busy_started: float | None,
        busy_elapsed: float,
    ) -> tuple[float | None, float]:
        """Track time spent in editor busy/reload states after dispatch."""
        is_busy = bool(health and not getattr(health, "ready", True))
        if is_busy and busy_started is None:
            return now, busy_elapsed
        if not is_busy and busy_started is not None:
            return None, busy_elapsed + (now - busy_started)
        return busy_started, busy_elapsed

    def _response_timeout_result(
        self,
        command_file: Path,
        command_id: str,
        elapsed: float,
        timeout: float,
        health: Any | None,
    ) -> CommandResult:
        """Return a timeout result with operation-state aware cleanup."""
        record = self._operation_store.load(command_id)
        if record is None or record.state == "queued":
            command_file.unlink(missing_ok=True)
            self._operation_store.transition(
                command_id,
                STATE_ABANDONED,
                reason=f"Command timed out before Unity accepted it after {timeout:.1f}s",
            )
        elif record.state not in {STATE_COMPLETED, STATE_FAILED, STATE_INTERRUPTED}:
            self._operation_store.transition(
                command_id,
                STATE_INTERRUPTED,
                reason=f"Command response timed out after {timeout:.1f}s",
                busy_reason=getattr(health, "busy_reason", None),
            )
        return CommandResult(
            success=False,
            error=f"Command timed out after {timeout:.1f}s",
            data={
                "status": "command_timeout",
                "retryable": False,
                "operationState": record.state if record else None,
            },
            command_id=command_id,
            execution_time_ms=int(elapsed * 1000),
            exit_code=1,
        )

    def _busy_timeout_result(
        self,
        command_id: str,
        elapsed: float,
        health: Any | None,
    ) -> CommandResult:
        """Return a bounded wait timeout while Unity remains busy/reloading."""
        self._operation_store.transition(
            command_id,
            STATE_RECOVERING,
            reason="Unity remained busy while command was in flight",
            busy_reason=getattr(health, "busy_reason", None),
        )
        return CommandResult(
            success=False,
            error="Unity Editor stayed busy while waiting for command response",
            data={
                "status": "editor_busy",
                "retryable": True,
                "health": health.to_dict() if health else None,
            },
            command_id=command_id,
            execution_time_ms=int(elapsed * 1000),
            exit_code=4,
        )

    def _operation_domain_generation(self, command_id: str) -> int | None:
        """Return the generation captured when a command was queued."""
        record = self._operation_store.load(command_id)
        return record.domain_generation if record else None

    def _mark_recovering_after_reload(
        self,
        command_id: str,
        busy_reason: str | None,
    ) -> None:
        """Move accepted/running operations to recovery after a generation change."""
        record = self._operation_store.load(command_id)
        if record is None or record.state == STATE_RECOVERING:
            return
        if record.state not in {STATE_ACCEPTED, STATE_RUNNING}:
            return
        self._operation_store.transition(
            command_id,
            STATE_RECOVERING,
            reason="Unity domain generation changed while waiting",
            busy_reason=busy_reason,
        )

    @staticmethod
    def _domain_generation_changed(health: Any | None, origin: int | None) -> bool:
        """Whether current heartbeat proves a domain reload occurred."""
        current = getattr(health, "domain_generation", None)
        return origin is not None and current is not None and current != origin

    @staticmethod
    def _parse_data_json(response: dict[str, Any]) -> Any | None:
        """Parse the dataJson field from a response dict."""
        raw = response.get("dataJson")
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

    def _wait_for_editor_ready(self) -> Any:
        """Wait for editor readiness using the configured readiness timeout."""
        timeout = _editor_ready_timeout()
        return self._health_monitor.wait_for_ready(
            timeout_seconds=timeout,
            poll_interval=self.EDITOR_READY_POLL_INTERVAL,
        )

    @staticmethod
    def _readiness_failure(health: Any) -> CommandResult:
        """Build a pre-dispatch failure from health/readiness state."""
        if health.healthy or getattr(health, "busy_reason", None):
            busy_reason = getattr(health, "busy_reason", None) or "busy"
            return CommandResult(
                success=False,
                data={
                    "status": "editor_busy",
                    "retryable": True,
                    "health": health.to_dict(),
                },
                error=f"Unity Editor is busy {busy_reason}; command was not sent",
                exit_code=4,
            )
        return CommandResult(
            success=False,
            error=f"Unity Bridge not healthy: {health.reason}",
            exit_code=2,
        )


def _editor_ready_timeout() -> float:
    """Resolve editor readiness timeout from environment or default."""
    value = os.environ.get("UNITY_BRIDGE_EDITOR_READY_TIMEOUT")
    if value is None:
        return DirectBridge.DEFAULT_EDITOR_READY_TIMEOUT
    try:
        return float(value)
    except ValueError:
        logger.warning("Invalid UNITY_BRIDGE_EDITOR_READY_TIMEOUT=%r", value)
        return DirectBridge.DEFAULT_EDITOR_READY_TIMEOUT


def _in_flight_busy_grace() -> float:
    """Resolve hard grace for in-flight waits paused by editor busy states."""
    value = os.environ.get("UNITY_BRIDGE_IN_FLIGHT_BUSY_GRACE")
    if value is None:
        return DirectBridge.DEFAULT_IN_FLIGHT_BUSY_GRACE
    try:
        return float(value)
    except ValueError:
        logger.warning("Invalid UNITY_BRIDGE_IN_FLIGHT_BUSY_GRACE=%r", value)
        return DirectBridge.DEFAULT_IN_FLIGHT_BUSY_GRACE

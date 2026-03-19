"""
DirectBridge — async file-based communication with Unity Editor.

Migrated from direct_bridge.py. Provides the core command dispatch layer
that writes command JSON files and polls for response files.

All commands return CommandResult dataclass instead of raw dicts.
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiofiles

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

    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root)
        self.commands_path = self.project_root / ".claude" / "unity" / "commands"
        self.responses_path = self.project_root / ".claude" / "unity" / "responses"

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
        if check_health and self._health_monitor:
            health = self._health_monitor.check_health()
            if not health.healthy:
                return CommandResult(
                    success=False,
                    error=f"Unity Bridge not healthy: {health.reason}",
                    exit_code=2,
                )
            if health.is_compiling:
                logger.warning("Unity is compiling — command may be delayed")

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

        try:
            await self._write_command_file(command, command_file)
            logger.debug("Sent command: %s (ID: %s)", command_type, command_id)
            return await self._wait_for_response(
                response_file, command_file, command_id, timeout
            )
        except Exception as exc:
            logger.error("Error sending command: %s", exc)
            command_file.unlink(missing_ok=True)
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

    async def _write_command_file(
        self, command: dict[str, Any], command_file: Path
    ) -> None:
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
        await asyncio.sleep(self.MIN_RESPONSE_DELAY)

        while True:
            elapsed = asyncio.get_running_loop().time() - start
            if elapsed > timeout:
                command_file.unlink(missing_ok=True)
                return CommandResult(
                    success=False,
                    error=f"Command timed out after {timeout:.1f}s",
                    command_id=command_id,
                    execution_time_ms=int(elapsed * 1000),
                    exit_code=1,
                )

            if response_file.exists():
                result = await self._try_read_response(
                    response_file, command_id, elapsed
                )
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
            return None

        response_file.unlink(missing_ok=True)

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

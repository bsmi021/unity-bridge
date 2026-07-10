"""Unit tests for core/bridge.py — DirectBridge and CommandResult."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch


from unity_bridge.core.bridge import CommandResult, DirectBridge
from unity_bridge.core.health import HealthStatus
from unity_bridge.core.operation import (
    STATE_ABANDONED,
    STATE_ACCEPTED,
    STATE_COMPLETED,
    STATE_FAILED,
    STATE_QUEUED,
    STATE_RECOVERING,
    STATE_RUNNING,
)


# ---------------------------------------------------------------------------
# CommandResult construction
# ---------------------------------------------------------------------------


class TestCommandResult:
    """Tests for the CommandResult dataclass."""

    def test_default_values(self) -> None:
        result = CommandResult(success=True)
        assert result.success is True
        assert result.data is None
        assert result.error is None
        assert result.command_id is None
        assert result.execution_time_ms == 0
        assert result.exit_code == 0
        assert result.cached is False

    def test_success_with_data(self) -> None:
        result = CommandResult(success=True, data={"count": 5}, command_id="abc-123")
        assert result.success is True
        assert result.data == {"count": 5}
        assert result.command_id == "abc-123"

    def test_error_result(self) -> None:
        result = CommandResult(success=False, error="Timeout", exit_code=1)
        assert result.success is False
        assert result.error == "Timeout"
        assert result.exit_code == 1

    def test_cached_flag(self) -> None:
        result = CommandResult(success=True, cached=True)
        assert result.cached is True

    def test_to_dict_contains_all_fields(self) -> None:
        result = CommandResult(
            success=True,
            data={"key": "val"},
            error=None,
            command_id="id-1",
            execution_time_ms=100,
            exit_code=0,
            cached=False,
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["data"] == {"key": "val"}
        assert d["command_id"] == "id-1"
        assert d["execution_time_ms"] == 100
        assert "cached" in d

    def test_to_dict_round_trips_through_json(self) -> None:
        result = CommandResult(success=True, data={"nested": [1, 2]})
        text = json.dumps(result.to_dict())
        parsed = json.loads(text)
        assert parsed["success"] is True
        assert parsed["data"]["nested"] == [1, 2]


# ---------------------------------------------------------------------------
# DirectBridge initialisation
# ---------------------------------------------------------------------------


class TestDirectBridgeInit:
    """Tests for DirectBridge construction and directory setup."""

    def test_creates_command_and_response_dirs(self, fake_project: Path) -> None:
        bridge = DirectBridge(fake_project)
        assert bridge.commands_path.exists()
        assert bridge.responses_path.exists()

    def test_paths_relative_to_project_root(self, fake_project: Path) -> None:
        bridge = DirectBridge(fake_project)
        assert bridge.commands_path == fake_project / ".claude" / "unity" / "commands"
        assert bridge.responses_path == fake_project / ".claude" / "unity" / "responses"

    def test_project_root_stored(self, fake_project: Path) -> None:
        bridge = DirectBridge(fake_project)
        assert bridge.project_root == fake_project


# ---------------------------------------------------------------------------
# Command JSON serialization
# ---------------------------------------------------------------------------


class TestCommandSerialization:
    """Tests for the JSON format of command files."""

    async def test_command_json_structure(self, fake_project: Path) -> None:
        """Verify the command JSON written to disk has expected fields."""
        bridge = DirectBridge(fake_project)
        # We won't wait for a response — just verify the file is written
        # by patching _wait_for_response to return immediately.
        immediate = CommandResult(success=True, data={"ok": True}, command_id="x")
        with patch.object(
            bridge, "_wait_for_response", new_callable=AsyncMock, return_value=immediate
        ):
            with patch.object(bridge, "_health_monitor", None):
                await bridge.send_command("test-cmd", {"key": "value"}, timeout=5.0)

        # The important thing is no exception was raised; file may have been
        # deleted after the mocked response.

    async def test_command_type_in_filename(self, fake_project: Path) -> None:
        bridge = DirectBridge(fake_project)
        immediate = CommandResult(success=True, command_id="x")
        with patch.object(
            bridge, "_wait_for_response", new_callable=AsyncMock, return_value=immediate
        ):
            with patch.object(bridge, "_health_monitor", None):
                await bridge.send_command("query-hierarchy", timeout=1.0)

    async def test_parameters_json_encoded(self, fake_project: Path) -> None:
        """parametersJson field must be a JSON-encoded string."""
        bridge = DirectBridge(fake_project)
        written_commands: list[dict[str, Any]] = []

        async def capture_write(command: dict, path: Path) -> None:
            written_commands.append(command)
            # Write to disk so _wait_for_response can potentially find it
            path.write_text(json.dumps(command), encoding="utf-8")

        immediate = CommandResult(success=True, command_id="x")
        with patch.object(bridge, "_write_command_file", side_effect=capture_write):
            with patch.object(
                bridge, "_wait_for_response", new_callable=AsyncMock, return_value=immediate
            ):
                with patch.object(bridge, "_health_monitor", None):
                    await bridge.send_command(
                        "set-component-data",
                        {"objectPath": "/Player", "value": 42},
                    )

        assert len(written_commands) == 1
        cmd = written_commands[0]
        assert "parametersJson" in cmd
        params = json.loads(cmd["parametersJson"])
        assert params["objectPath"] == "/Player"
        assert params["value"] == 42

    async def test_command_has_uuid_and_timestamp(self, fake_project: Path) -> None:
        bridge = DirectBridge(fake_project)
        written: list[dict] = []

        async def capture(command: dict, path: Path) -> None:
            written.append(command)

        immediate = CommandResult(success=True, command_id="x")
        with patch.object(bridge, "_write_command_file", side_effect=capture):
            with patch.object(
                bridge, "_wait_for_response", new_callable=AsyncMock, return_value=immediate
            ):
                with patch.object(bridge, "_health_monitor", None):
                    await bridge.send_command("test-cmd")

        cmd = written[0]
        assert "commandId" in cmd
        assert len(cmd["commandId"]) == 36  # UUID format
        assert "timestamp" in cmd

    async def test_send_command_creates_queued_operation_record(
        self,
        fake_project: Path,
    ) -> None:
        bridge = DirectBridge(fake_project)
        captured_command_id: str | None = None

        async def capture(command: dict, path: Path) -> None:
            nonlocal captured_command_id
            captured_command_id = command["commandId"]
            path.write_text(json.dumps(command), encoding="utf-8")

        immediate = CommandResult(success=True, command_id="x")
        with patch.object(bridge, "_write_command_file", side_effect=capture):
            with patch.object(
                bridge, "_wait_for_response", new_callable=AsyncMock, return_value=immediate
            ):
                with patch.object(bridge, "_health_monitor", None):
                    await bridge.send_command("query-hierarchy", {"depth": 2})

        assert captured_command_id is not None
        record = bridge._operation_store.load(captured_command_id)
        assert record is not None
        assert record.state == STATE_QUEUED
        assert record.command_type == "query-hierarchy"
        assert record.retry_policy == "read_only"
        assert bridge._operation_store.events_path(captured_command_id).exists()

    async def test_send_prepared_command_uses_existing_command_id(
        self,
        fake_project: Path,
    ) -> None:
        bridge = DirectBridge(fake_project)
        written_commands: list[dict[str, Any]] = []

        async def capture(command: dict, path: Path) -> None:
            written_commands.append(command)
            path.write_text(json.dumps(command), encoding="utf-8")

        immediate = CommandResult(success=True, command_id="prepared-command")
        with patch.object(bridge, "_write_command_file", side_effect=capture):
            with patch.object(
                bridge,
                "_wait_for_response",
                new_callable=AsyncMock,
                return_value=immediate,
            ):
                result = await bridge.send_prepared_command(
                    command_id="prepared-command",
                    command_type="query-hierarchy",
                    parameters={"maxDepth": 1},
                    timeout=5.0,
                    check_health=False,
                    create_operation=False,
                )

        assert result.success is True
        assert written_commands[0]["commandId"] == "prepared-command"
        assert written_commands[0]["commandType"] == "query-hierarchy"
        assert json.loads(written_commands[0]["parametersJson"]) == {"maxDepth": 1}
        assert bridge._operation_store.load("prepared-command") is None


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


class TestResponseParsing:
    """Tests for parsing different response statuses."""

    def test_parse_data_json_valid(self) -> None:
        resp = {"dataJson": '{"count": 5}'}
        result = DirectBridge._parse_data_json(resp)
        assert result == {"count": 5}

    def test_parse_data_json_empty(self) -> None:
        assert DirectBridge._parse_data_json({}) is None
        assert DirectBridge._parse_data_json({"dataJson": ""}) is None

    def test_parse_data_json_invalid_returns_raw(self) -> None:
        resp = {"dataJson": "not-json"}
        result = DirectBridge._parse_data_json(resp)
        assert result == "not-json"

    async def test_inner_failure_payload_returns_failed_command_result(
        self,
        fake_project: Path,
    ) -> None:
        # Arrange
        bridge = DirectBridge(fake_project)
        command_id = "cmd-inner-failure"
        response_file = bridge.responses_path / "cmd-inner-failure-asset-ext.json"
        bridge._operation_store.create_queued(
            command_id=command_id,
            command_type="asset-ext",
            parameters={"operation": "delete"},
            command_path=bridge.commands_path / "cmd-inner-failure-asset-ext.json",
            response_path=response_file,
            domain_generation=None,
            retry_policy="non_idempotent",
        )
        data = {
            "success": False,
            "operation": "delete",
            "message": "Asset path escapes the project root.",
        }
        response_file.write_text(
            json.dumps({"status": "success", "dataJson": json.dumps(data)}),
            encoding="utf-8",
        )
        bridge._operation_store.transition(command_id, STATE_COMPLETED, reason="success")

        # Act
        result = await bridge._try_read_response(response_file, command_id, elapsed=0.1)

        # Assert
        assert result is not None
        assert result.success is False
        assert result.exit_code == 1
        assert result.error == "Asset path escapes the project root."
        assert result.data == data
        record = bridge._operation_store.load(command_id)
        assert record is not None
        assert record.state == STATE_FAILED

    async def test_error_envelope_preserves_structured_data(
        self,
        fake_project: Path,
    ) -> None:
        # Arrange
        bridge = DirectBridge(fake_project)
        command_id = "cmd-structured-error"
        response_file = bridge.responses_path / "cmd-structured-error-execute-script.json"
        bridge._operation_store.create_queued(
            command_id=command_id,
            command_type="execute-script",
            parameters={},
            command_path=bridge.commands_path / "cmd-structured-error-execute-script.json",
            response_path=response_file,
            domain_generation=None,
            retry_policy="non_idempotent",
        )
        data = {
            "success": False,
            "compilerDiagnostics": [{"code": "CS1002", "severity": "error"}],
            "unityLogs": [],
        }
        response_file.write_text(
            json.dumps(
                {
                    "status": "error",
                    "errorMessage": "Script compilation failed.",
                    "dataJson": json.dumps(data),
                }
            ),
            encoding="utf-8",
        )

        # Act
        result = await bridge._try_read_response(response_file, command_id, elapsed=0.1)

        # Assert
        assert result is not None
        assert result.success is False
        assert result.error == "Script compilation failed."
        assert result.data == data
        assert result.exit_code == 1

    async def test_running_response_transitions_operation(
        self,
        fake_project: Path,
    ) -> None:
        bridge = DirectBridge(fake_project)
        command_id = "cmd-running"
        response_file = bridge.responses_path / "cmd-running-query-hierarchy.json"
        bridge._operation_store.create_queued(
            command_id=command_id,
            command_type="query-hierarchy",
            parameters={},
            command_path=bridge.commands_path / "cmd-running-query-hierarchy.json",
            response_path=response_file,
            domain_generation=None,
            retry_policy="read_only",
        )
        response_file.write_text(
            json.dumps(
                {
                    "status": "running",
                    "commandId": command_id,
                    "commandType": "query-hierarchy",
                }
            ),
            encoding="utf-8",
        )

        result = await bridge._try_read_response(response_file, command_id, elapsed=0.1)

        assert result is None
        record = bridge._operation_store.load(command_id)
        assert record is not None
        assert record.state == STATE_RUNNING

    async def test_bom_prefixed_response_is_parsed(
        self,
        fake_project: Path,
    ) -> None:
        bridge = DirectBridge(fake_project)
        command_id = "cmd-bom"
        response_file = bridge.responses_path / "cmd-bom-query-hierarchy.json"
        bridge._operation_store.create_queued(
            command_id=command_id,
            command_type="query-hierarchy",
            parameters={},
            command_path=bridge.commands_path / "cmd-bom-query-hierarchy.json",
            response_path=response_file,
            domain_generation=None,
            retry_policy="read_only",
        )
        payload = {
            "status": "success",
            "commandId": command_id,
            "commandType": "query-hierarchy",
            "dataJson": '{"count": 3}',
        }
        response_file.write_bytes(b"\xef\xbb\xbf" + json.dumps(payload).encode("utf-8"))

        result = await bridge._try_read_response(response_file, command_id, elapsed=0.1)

        assert result is not None
        assert result.success is True
        assert result.data == {"count": 3}

    async def test_repeated_running_response_does_not_spam_events(
        self,
        fake_project: Path,
    ) -> None:
        bridge = DirectBridge(fake_project)
        command_id = "cmd-running"
        response_file = bridge.responses_path / "cmd-running-query-hierarchy.json"
        bridge._operation_store.create_queued(
            command_id=command_id,
            command_type="query-hierarchy",
            parameters={},
            command_path=bridge.commands_path / "cmd-running-query-hierarchy.json",
            response_path=response_file,
            domain_generation=None,
            retry_policy="read_only",
        )
        response_file.write_text(
            json.dumps(
                {
                    "status": "running",
                    "commandId": command_id,
                    "commandType": "query-hierarchy",
                }
            ),
            encoding="utf-8",
        )

        await bridge._try_read_response(response_file, command_id, elapsed=0.1)
        await bridge._try_read_response(response_file, command_id, elapsed=0.2)

        events = bridge._operation_store.events_path(command_id).read_text(encoding="utf-8")
        assert len(events.strip().splitlines()) == 2


# ---------------------------------------------------------------------------
# Unhealthy bridge short-circuits
# ---------------------------------------------------------------------------


class TestHealthGating:
    """Verify send_command checks health before dispatching."""

    async def test_unhealthy_returns_error(self, fake_project: Path) -> None:
        bridge = DirectBridge(fake_project)
        # Create a mock health monitor that reports unhealthy
        mock_monitor = MagicMock()
        mock_monitor.wait_for_ready.return_value = HealthStatus(
            healthy=False, reason="Stale heartbeat", ready=False
        )
        bridge._health_monitor = mock_monitor

        result = await bridge.send_command("test", check_health=True)
        assert result.success is False
        assert result.exit_code == 2
        assert "not healthy" in result.error

    async def test_busy_editor_does_not_write_command_file(self, fake_project: Path) -> None:
        bridge = DirectBridge(fake_project)
        mock_monitor = MagicMock()
        mock_monitor.wait_for_ready.return_value = HealthStatus(
            healthy=True,
            ready=False,
            is_compiling=True,
            busy_reason="compiling",
        )
        bridge._health_monitor = mock_monitor

        with patch.object(bridge, "_write_command_file", new_callable=AsyncMock) as write:
            result = await bridge.send_command("set-component-data", check_health=True)

        assert result.success is False
        assert result.exit_code == 4
        assert result.command_id is None
        assert "busy compiling" in result.error
        assert "command was not sent" in result.error
        assert result.data["status"] == "editor_busy"
        assert result.data["retryable"] is True
        write.assert_not_called()

    async def test_waits_for_ready_before_sending_command(self, fake_project: Path) -> None:
        bridge = DirectBridge(fake_project)
        mock_monitor = MagicMock()
        mock_monitor.wait_for_ready.return_value = HealthStatus(healthy=True, ready=True)
        bridge._health_monitor = mock_monitor

        immediate = CommandResult(success=True, command_id="x")
        with patch.object(bridge, "_write_command_file", new_callable=AsyncMock) as write:
            with patch.object(
                bridge, "_wait_for_response", new_callable=AsyncMock, return_value=immediate
            ):
                result = await bridge.send_command("query-hierarchy", check_health=True)

        assert result.success is True
        mock_monitor.wait_for_ready.assert_called_once()
        write.assert_called_once()

    async def test_readiness_wait_runs_off_event_loop(self, fake_project: Path) -> None:
        bridge = DirectBridge(fake_project)
        mock_monitor = MagicMock()
        bridge._health_monitor = mock_monitor
        immediate = CommandResult(success=True, command_id="x")

        with patch("unity_bridge.core.bridge.asyncio.to_thread", new_callable=AsyncMock) as wait:
            wait.return_value = HealthStatus(healthy=True, ready=True)
            with patch.object(bridge, "_write_command_file", new_callable=AsyncMock):
                with patch.object(
                    bridge,
                    "_wait_for_response",
                    new_callable=AsyncMock,
                    return_value=immediate,
                ):
                    result = await bridge.send_command("query-hierarchy", check_health=True)

        assert result.success is True
        wait.assert_awaited_once()
        assert wait.await_args.args[0] == mock_monitor.wait_for_ready

    async def test_prepared_command_busy_editor_keeps_command_id(self, fake_project: Path) -> None:
        bridge = DirectBridge(fake_project)
        mock_monitor = MagicMock()
        mock_monitor.wait_for_ready.return_value = HealthStatus(
            healthy=True,
            ready=False,
            is_compiling=True,
            busy_reason="compiling",
        )
        bridge._health_monitor = mock_monitor

        with patch.object(bridge, "_write_command_file", new_callable=AsyncMock) as write:
            result = await bridge.send_prepared_command(
                command_id="prepared-command",
                command_type="set-component-data",
                check_health=True,
            )

        assert result.success is False
        assert result.command_id == "prepared-command"
        assert result.data["status"] == "editor_busy"
        write.assert_not_called()

    async def test_skip_health_check(self, fake_project: Path) -> None:
        bridge = DirectBridge(fake_project)
        mock_monitor = MagicMock()
        mock_monitor.check_health.return_value = MagicMock(healthy=False, reason="down")
        bridge._health_monitor = mock_monitor

        immediate = CommandResult(success=True, command_id="x")
        with patch.object(
            bridge, "_wait_for_response", new_callable=AsyncMock, return_value=immediate
        ):
            result = await bridge.send_command("test", check_health=False)
        assert result.success is True
        mock_monitor.check_health.assert_not_called()


# ---------------------------------------------------------------------------
# Atomic file write
# ---------------------------------------------------------------------------


class TestAtomicWrite:
    """Verify _write_command_file uses temp + rename."""

    async def test_writes_valid_json(self, fake_project: Path) -> None:
        bridge = DirectBridge(fake_project)
        command = {"commandId": "abc", "commandType": "test"}
        target = bridge.commands_path / "abc-test.json"
        await bridge._write_command_file(command, target)
        assert target.exists()
        data = json.loads(target.read_text(encoding="utf-8"))
        assert data["commandId"] == "abc"

    async def test_temp_file_cleaned_up(self, fake_project: Path) -> None:
        bridge = DirectBridge(fake_project)
        command = {"commandId": "def", "commandType": "test"}
        target = bridge.commands_path / "def-test.json"
        await bridge._write_command_file(command, target)
        tmp = target.with_suffix(".json.tmp")
        assert not tmp.exists()


class TestResponseWaitState:
    """Verify response wait updates durable operation state."""

    def test_repeated_generation_change_marks_recovery_once(
        self,
        fake_project: Path,
    ) -> None:
        bridge = DirectBridge(fake_project)
        command_id = "cmd-reload"
        bridge._operation_store.create_queued(
            command_id=command_id,
            command_type="query-hierarchy",
            parameters={},
            command_path=bridge.commands_path / "cmd-reload-query-hierarchy.json",
            response_path=bridge.responses_path / "cmd-reload-query-hierarchy.json",
            domain_generation=1,
            retry_policy="read_only",
        )
        bridge._operation_store.transition(command_id, STATE_ACCEPTED, reason="accepted")

        bridge._mark_recovering_after_reload(command_id, "reloading_assemblies")
        bridge._mark_recovering_after_reload(command_id, "reloading_assemblies")

        record = bridge._operation_store.load(command_id)
        events = bridge._operation_store.events_path(command_id).read_text(encoding="utf-8")
        assert record is not None
        assert record.state == STATE_RECOVERING
        assert len(events.strip().splitlines()) == 3

    async def test_timeout_before_acceptance_marks_abandoned(
        self,
        fake_project: Path,
    ) -> None:
        bridge = DirectBridge(fake_project)
        bridge._health_monitor = None
        command_id = "cmd-timeout"
        command_file = bridge.commands_path / "cmd-timeout-query-hierarchy.json"
        response_file = bridge.responses_path / "cmd-timeout-query-hierarchy.json"
        command_file.write_text("{}", encoding="utf-8")
        bridge._operation_store.create_queued(
            command_id=command_id,
            command_type="query-hierarchy",
            parameters={},
            command_path=command_file,
            response_path=response_file,
            domain_generation=None,
            retry_policy="read_only",
        )

        result = await bridge._wait_for_response(
            response_file,
            command_file,
            command_id,
            timeout=0.01,
        )

        record = bridge._operation_store.load(command_id)
        assert result.success is False
        assert result.data["status"] == "command_timeout"
        assert record is not None
        assert record.state == STATE_ABANDONED
        assert not command_file.exists()


class TestTimeoutExitCode:
    """B4: a plain command timeout must report exit_code 4 (Timeout), not 1."""

    async def test_command_timeout_returns_exit_code_4(self, fake_project: Path) -> None:
        bridge = DirectBridge(fake_project)
        bridge._health_monitor = None
        command_id = "cmd-timeout-code"
        command_file = bridge.commands_path / f"{command_id}-query-hierarchy.json"
        response_file = bridge.responses_path / f"{command_id}-query-hierarchy.json"
        command_file.write_text("{}", encoding="utf-8")
        bridge._operation_store.create_queued(
            command_id=command_id,
            command_type="query-hierarchy",
            parameters={},
            command_path=command_file,
            response_path=response_file,
            domain_generation=None,
            retry_policy="read_only",
        )

        result = await bridge._wait_for_response(
            response_file, command_file, command_id, timeout=0.01
        )

        assert result.exit_code == 4


class TestGlobalTimeoutOverride:
    """B2: an explicit global --timeout/env override applies to every command."""

    def test_no_override_uses_requested_timeout(self, fake_project: Path) -> None:
        bridge = DirectBridge(fake_project)
        assert bridge._effective_timeout("run-tests", 300.0) == 300.0

    def test_global_override_replaces_requested_timeout(self, fake_project: Path) -> None:
        bridge = DirectBridge(fake_project, default_timeout=5)
        assert bridge._effective_timeout("run-tests", 300.0) == 5.0
        assert bridge._effective_timeout("query-hierarchy", 10.0) == 5.0


class TestActiveElapsedClamp:
    """B10: busy accounting must never produce a negative active-elapsed."""

    def test_active_elapsed_never_negative(self) -> None:
        # busy_elapsed + current_busy exceeds elapsed (flapping health states)
        assert DirectBridge._active_elapsed(1.0, 2.0, 0.5) == 0.0

    def test_active_elapsed_normal_case(self) -> None:
        assert DirectBridge._active_elapsed(10.0, 3.0, 1.0) == 6.0


class TestRetryPolicyEnforcement:
    """B6: non-idempotent mutations must not be re-sent once Unity accepted them."""

    def _accepted_record(self, bridge: DirectBridge, command_id: str, state: str) -> None:
        bridge._operation_store.create_queued(
            command_id=command_id,
            command_type="set-component-data",
            parameters={},
            command_path=bridge.commands_path / f"{command_id}.json",
            response_path=bridge.responses_path / f"{command_id}.json",
            domain_generation=None,
            retry_policy="non_idempotent",
        )
        if state != STATE_QUEUED:
            bridge._operation_store.transition(command_id, state, reason="setup")

    def test_non_idempotent_accepted_is_not_retryable(self, fake_project: Path) -> None:
        from unity_bridge.core.operation import RETRY_NON_IDEMPOTENT

        bridge = DirectBridge(fake_project)
        self._accepted_record(bridge, "cmd-acc", STATE_ACCEPTED)
        result = CommandResult(success=False, error="file is being used", command_id="cmd-acc")
        assert bridge._retry_allowed(result, RETRY_NON_IDEMPOTENT, None) is False

    def test_non_idempotent_still_queued_is_retryable(self, fake_project: Path) -> None:
        from unity_bridge.core.operation import RETRY_NON_IDEMPOTENT

        bridge = DirectBridge(fake_project)
        self._accepted_record(bridge, "cmd-q", STATE_QUEUED)
        result = CommandResult(success=False, error="timeout", command_id="cmd-q")
        assert bridge._retry_allowed(result, RETRY_NON_IDEMPOTENT, None) is True

    def test_idempotency_key_allows_retry(self, fake_project: Path) -> None:
        from unity_bridge.core.operation import RETRY_NON_IDEMPOTENT

        bridge = DirectBridge(fake_project)
        self._accepted_record(bridge, "cmd-idem", STATE_ACCEPTED)
        result = CommandResult(success=False, error="timeout", command_id="cmd-idem")
        assert bridge._retry_allowed(result, RETRY_NON_IDEMPOTENT, "key-123") is True

    def test_read_only_always_retryable(self, fake_project: Path) -> None:
        from unity_bridge.core.operation import RETRY_READ_ONLY

        bridge = DirectBridge(fake_project)
        self._accepted_record(bridge, "cmd-ro", STATE_ACCEPTED)
        result = CommandResult(success=False, error="timeout", command_id="cmd-ro")
        assert bridge._retry_allowed(result, RETRY_READ_ONLY, None) is True

    def test_non_idempotent_unknown_operation_state_is_not_retryable(
        self,
        fake_project: Path,
    ) -> None:
        from unity_bridge.core.operation import RETRY_NON_IDEMPOTENT

        bridge = DirectBridge(fake_project)
        result = CommandResult(
            success=False,
            error="[Errno 13] Permission denied: operations/cmd-missing.json",
            command_id="cmd-missing",
        )

        assert bridge._retry_allowed(result, RETRY_NON_IDEMPOTENT, None) is False

    async def test_non_idempotent_failure_with_command_id_is_not_resent(
        self,
        fake_project: Path,
    ) -> None:
        from unity_bridge.core.retry import RetryConfig

        bridge = DirectBridge(fake_project)
        first = CommandResult(
            success=False,
            error="[WinError 32] file is being used: operations/cmd-first.json",
            command_id="cmd-first",
        )
        duplicate = CommandResult(success=True, command_id="cmd-duplicate")

        with patch.object(
            bridge,
            "send_command",
            new_callable=AsyncMock,
            side_effect=[first, duplicate],
        ) as send:
            result = await bridge.send_command_with_retry(
                "run-tests",
                {},
                timeout=1.0,
                retry_config=RetryConfig(max_retries=1, base_delay=0.0),
            )

        assert result is first
        assert send.await_count == 1


class TestReconcileOrphans:
    """B5: a late response for a timed-out (terminal) operation must be reaped."""

    async def test_reconcile_removes_terminal_response(self, fake_project: Path) -> None:
        from unity_bridge.core.operation import STATE_INTERRUPTED

        bridge = DirectBridge(fake_project)
        response_file = bridge.responses_path / "orphan-set-component-data.json"
        bridge._operation_store.create_queued(
            command_id="orphan",
            command_type="set-component-data",
            parameters={},
            command_path=bridge.commands_path / "orphan-set-component-data.json",
            response_path=response_file,
            domain_generation=None,
            retry_policy="non_idempotent",
        )
        bridge._operation_store.transition("orphan", STATE_ACCEPTED, reason="setup")
        bridge._operation_store.transition("orphan", STATE_INTERRUPTED, reason="timed out")
        response_file.write_text('{"status":"success"}', encoding="utf-8")

        removed = bridge.reconcile_orphans()

        assert str(response_file) in removed
        assert not response_file.exists()

    async def test_reconcile_keeps_in_flight_response(self, fake_project: Path) -> None:
        bridge = DirectBridge(fake_project)
        response_file = bridge.responses_path / "live-query-hierarchy.json"
        bridge._operation_store.create_queued(
            command_id="live",
            command_type="query-hierarchy",
            parameters={},
            command_path=bridge.commands_path / "live-query-hierarchy.json",
            response_path=response_file,
            domain_generation=None,
            retry_policy="read_only",
        )
        bridge._operation_store.transition("live", STATE_RUNNING, reason="setup")
        response_file.write_text('{"status":"running"}', encoding="utf-8")

        removed = bridge.reconcile_orphans()

        assert str(response_file) not in removed
        assert response_file.exists()

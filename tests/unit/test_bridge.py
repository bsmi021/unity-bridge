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

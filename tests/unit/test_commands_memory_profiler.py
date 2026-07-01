"""Unit tests for commands/memory_profiler.py — MemoryProfiler snapshot capture."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from typer.testing import CliRunner

from unity_bridge.commands.memory_profiler import (
    memory_profiler_app,
    memory_profiler_take_snapshot,
)
from unity_bridge.core.output import OutputFormatter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_parameters(call_args: Any) -> dict:
    if call_args.kwargs.get("parameters") is not None:
        return call_args.kwargs["parameters"]
    if len(call_args.args) >= 2:
        return call_args.args[1]
    return {}


def _extract_command_type(call_args: Any) -> str:
    if "command_type" in call_args.kwargs:
        return call_args.kwargs["command_type"]
    return call_args.args[0]


def _extract_kwarg(call_args: Any, key: str) -> Any:
    if key in call_args.kwargs:
        return call_args.kwargs[key]
    return None


def _state(mock_bridge: MagicMock) -> SimpleNamespace:
    return SimpleNamespace(bridge=mock_bridge, formatter=OutputFormatter())


def _run_memory_profiler(args: list[str], mock_bridge: MagicMock):
    runner = CliRunner()
    return runner.invoke(memory_profiler_app, args, obj=_state(mock_bridge))


# ---------------------------------------------------------------------------
# memory_profiler_take_snapshot — core async function
# ---------------------------------------------------------------------------


class TestMemoryProfilerTakeSnapshot:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await memory_profiler_take_snapshot(mock_bridge)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "memory-profiler"

    async def test_sends_take_snapshot_operation(self, mock_bridge: MagicMock) -> None:
        await memory_profiler_take_snapshot(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "take-snapshot"

    async def test_no_path_or_flags_omits_both(self, mock_bridge: MagicMock) -> None:
        await memory_profiler_take_snapshot(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "take-snapshot"}
        assert "path" not in params
        assert "captureFlags" not in params

    async def test_explicit_path_passed_through_unchanged(self, mock_bridge: MagicMock) -> None:
        await memory_profiler_take_snapshot(mock_bridge, path="Snapshots/manual.snap")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["path"] == "Snapshots/manual.snap"

    async def test_explicit_capture_flags_passed_through_as_camel_case(
        self, mock_bridge: MagicMock
    ) -> None:
        await memory_profiler_take_snapshot(
            mock_bridge, capture_flags="ManagedObjects,NativeObjects"
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["captureFlags"] == "ManagedObjects,NativeObjects"

    async def test_path_and_capture_flags_together(self, mock_bridge: MagicMock) -> None:
        await memory_profiler_take_snapshot(
            mock_bridge,
            path="Snapshots/manual.snap",
            capture_flags="ManagedObjects",
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {
            "operation": "take-snapshot",
            "path": "Snapshots/manual.snap",
            "captureFlags": "ManagedObjects",
        }

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        await memory_profiler_take_snapshot(mock_bridge)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 120.0

    async def test_custom_timeout_propagates(self, mock_bridge: MagicMock) -> None:
        await memory_profiler_take_snapshot(mock_bridge, timeout=30.0)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 30.0

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await memory_profiler_take_snapshot(failing_bridge)
        assert result.success is False

    async def test_uses_send_command_with_retry_not_send_command(
        self, mock_bridge: MagicMock
    ) -> None:
        await memory_profiler_take_snapshot(mock_bridge)
        assert mock_bridge.send_command_with_retry.call_count == 1
        assert mock_bridge.send_command.call_count == 0

    async def test_returns_command_result_with_running_status_data(
        self, mock_bridge: MagicMock
    ) -> None:
        from unity_bridge.core.bridge import CommandResult

        expected = CommandResult(
            success=True,
            data={"status": "running", "message": "Snapshot capture started"},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await memory_profiler_take_snapshot(mock_bridge)
        assert result.data["status"] == "running"


# ---------------------------------------------------------------------------
# CLI wrapper
# ---------------------------------------------------------------------------


class TestMemoryProfilerTakeSnapshotCli:
    def test_take_snapshot_cli_no_args(self, mock_bridge: MagicMock) -> None:
        result = _run_memory_profiler(["take-snapshot"], mock_bridge)

        assert result.exit_code == 0
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "take-snapshot"}

    def test_take_snapshot_cli_with_path_and_flags(self, mock_bridge: MagicMock) -> None:
        result = _run_memory_profiler(
            [
                "take-snapshot",
                "--path",
                "Snapshots/manual.snap",
                "--capture-flags",
                "ManagedObjects,NativeObjects",
            ],
            mock_bridge,
        )

        assert result.exit_code == 0
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {
            "operation": "take-snapshot",
            "path": "Snapshots/manual.snap",
            "captureFlags": "ManagedObjects,NativeObjects",
        }

    def test_take_snapshot_cli_failure_path(self, failing_bridge: MagicMock) -> None:
        result = _run_memory_profiler(["take-snapshot"], failing_bridge)

        assert result.exit_code != 0

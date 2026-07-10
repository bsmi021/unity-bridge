"""Behavior and source-contract tests for cooperative execute-script jobs."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock


ROOT = Path(__file__).resolve().parents[2]
BRIDGE_DIR = ROOT / "ClaudeCodeBridge"


async def test_execute_job_waits_with_a_client_deadline_cushion(
    mock_bridge: MagicMock,
) -> None:
    # Arrange
    from unity_bridge.commands import scripting_job_cli as scripting

    # Act
    await scripting.execute_script_job(
        mock_bridge,
        expression="new DelegateExecuteScriptJob(() => ExecuteScriptJobStep.Complete(42))",
        timeout=20,
    )

    # Assert
    call = mock_bridge.send_command_with_retry.call_args
    assert call.kwargs["command_type"] == "execute-job"
    assert call.kwargs["parameters"]["manifest"]["timeoutMs"] == 20_000
    assert call.kwargs["timeout"] > 20


def test_detached_job_queues_the_same_governed_payload(monkeypatch: Any, tmp_path: Path) -> None:
    # Arrange
    from unity_bridge.commands import scripting_job_cli as scripting

    captured: dict[str, Any] = {}

    def fake_submit(
        project_root: Path,
        command_type: str,
        parameters: dict[str, Any],
        *,
        timeout: float,
    ) -> object:
        captured.update(
            project_root=project_root,
            command_type=command_type,
            parameters=parameters,
            timeout=timeout,
        )
        return object()

    monkeypatch.setattr(scripting, "submit_operation", fake_submit)

    # Act
    scripting.detach_execute_script_job(
        tmp_path,
        expression="new DelegateExecuteScriptJob(() => ExecuteScriptJobStep.Continue())",
        intent="mutating",
        undo_label="Cooperative mutation",
        declared_file_paths=["Assets/cooperative.asset"],
        timeout=15,
    )

    # Assert
    assert captured["project_root"] == tmp_path
    assert captured["command_type"] == "execute-job"
    assert captured["parameters"]["manifest"]["intent"] == "mutating"
    assert captured["parameters"]["manifest"]["undoLabel"] == "Cooperative mutation"
    assert captured["timeout"] == 20.0


async def test_cancel_job_targets_the_original_command(mock_bridge: MagicMock) -> None:
    # Arrange
    from unity_bridge.commands import scripting_job_cli as scripting

    # Act
    await scripting.cancel_execute_script_job(mock_bridge, "job-command-id")

    # Assert
    call = mock_bridge.send_command_with_retry.call_args
    assert call.kwargs["command_type"] == "cancel-execute-job"
    assert call.kwargs["parameters"] == {"targetCommandId": "job-command-id"}


def test_cooperative_job_contract_is_executable(tmp_path: Path) -> None:
    # Arrange
    project = tmp_path / "JobContracts.csproj"
    contract = BRIDGE_DIR / "ExecuteScriptJobContracts.cs"
    project.write_text(
        f"""<Project Sdk=\"Microsoft.NET.Sdk\">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>disable</ImplicitUsings>
    <Nullable>disable</Nullable>
  </PropertyGroup>
  <ItemGroup>
    <Compile Include=\"{contract.as_posix()}\" Link=\"ExecuteScriptJobContracts.cs\" />
    <Compile Include=\"{(BRIDGE_DIR / "ExecuteScriptJobController.cs").as_posix()}\" Link=\"ExecuteScriptJobController.cs\" />
  </ItemGroup>
</Project>
""",
        encoding="utf-8",
    )
    (tmp_path / "Program.cs").write_text(_job_contract_program(), encoding="utf-8")

    # Act
    completed = subprocess.run(
        ["dotnet", "run", "--project", str(project), "--nologo"],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1"},
    )

    # Assert
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_job_handlers_are_registered_and_advance_on_editor_updates() -> None:
    # Arrange
    registry = (BRIDGE_DIR / "BridgeCommandRegistry.cs").read_text(encoding="utf-8")
    handler = (BRIDGE_DIR / "ExecuteScriptJobCommandHandler.cs").read_text(encoding="utf-8")
    cancel_handler = (BRIDGE_DIR / "CancelExecuteScriptJobCommandHandler.cs").read_text(
        encoding="utf-8"
    )
    terminal_store = (BRIDGE_DIR / "ExecuteScriptJobTerminalStore.cs").read_text(encoding="utf-8")

    # Act / Assert
    assert "new ExecuteScriptJobCommandHandler()" in registry
    assert "new CancelExecuteScriptJobCommandHandler()" in registry
    assert 'CommandType => "execute-job"' in handler
    assert 'CommandType => "cancel-execute-job"' in cancel_handler
    assert "EditorApplication.update += UpdatePendingJob" in handler
    assert "BridgeResponse.Running" in handler
    assert "WriteResponseStatic" in terminal_store
    assert "CheckDeadline" in handler
    assert "RequestCancellation" in handler


def test_unexpected_job_failure_releases_the_active_coordinator_slot() -> None:
    # Arrange
    handler = (BRIDGE_DIR / "ExecuteScriptJobCommandHandler.cs").read_text(encoding="utf-8")

    # Act / Assert
    assert "if (_active.FailUnexpectedly(ex))" in handler
    assert "public bool FailUnexpectedly(Exception exception)" in handler


def test_job_sources_have_unity_meta_files() -> None:
    # Arrange
    sources = sorted(BRIDGE_DIR.glob("ExecuteScriptJob*.cs"))

    # Act
    missing = [source.name for source in sources if not Path(f"{source}.meta").is_file()]

    # Assert
    assert sources
    assert missing == []


def _job_contract_program() -> str:
    return r"""using System;
using BWS.Editor.ClaudeCodeBridge;

internal static class Program
{
    private static int Main()
    {
        if (!ContractWorks()) return 1;
        if (!ControllerCompletesOneStepPerAdvance()) return 2;
        if (!ControllerCancelsBeforeAnotherStep()) return 3;
        if (!ControllerTimesOutAfterAnOverrunningStep()) return 4;
        return 0;
    }

    private static bool ContractWorks()
    {
        var calls = 0;
        var cancelled = false;
        var job = new DelegateExecuteScriptJob(
            () => ++calls == 1
                ? ExecuteScriptJobStep.Continue("more")
                : ExecuteScriptJobStep.Complete(42, "done"),
            () => cancelled = true);
        var first = job.Step();
        var second = job.Step();
        job.Cancel();
        var failed = ExecuteScriptJobStep.Fail("expected");
        return !first.completed && first.success
            && second.completed && second.success && (int)second.result == 42
            && cancelled && failed.completed && !failed.success;
    }

    private static bool ControllerCompletesOneStepPerAdvance()
    {
        var now = 0L;
        var calls = 0;
        var job = new DelegateExecuteScriptJob(stepIndex =>
        {
            calls++;
            return stepIndex == 0
                ? ExecuteScriptJobStep.Continue()
                : ExecuteScriptJobStep.Complete(stepIndex);
        });
        var controller = new ExecuteScriptJobController(job, 100, () => now);
        var first = controller.Advance();
        var second = controller.Advance();
        var third = controller.Advance();
        return calls == 2
            && first.kind == ExecuteScriptJobAdvanceKind.Continue
            && second.kind == ExecuteScriptJobAdvanceKind.Completed
            && (int)second.step.result == 1
            && third.kind == ExecuteScriptJobAdvanceKind.AlreadyTerminal;
    }

    private static bool ControllerCancelsBeforeAnotherStep()
    {
        var calls = 0;
        var cancelled = false;
        var job = new DelegateExecuteScriptJob(
            () => { calls++; return ExecuteScriptJobStep.Continue(); },
            () => cancelled = true);
        var controller = new ExecuteScriptJobController(job, 100, () => 0);
        controller.RequestCancellation();
        var result = controller.Advance();
        return result.kind == ExecuteScriptJobAdvanceKind.Cancelled
            && calls == 0 && cancelled;
    }

    private static bool ControllerTimesOutAfterAnOverrunningStep()
    {
        var now = 0L;
        var calls = 0;
        var job = new DelegateExecuteScriptJob(() =>
        {
            calls++;
            now = 101;
            return ExecuteScriptJobStep.Complete("too late");
        });
        var controller = new ExecuteScriptJobController(job, 100, () => now);
        var result = controller.Advance();
        return result.kind == ExecuteScriptJobAdvanceKind.TimedOut
            && result.stepOverran && calls == 1;
    }
}
"""

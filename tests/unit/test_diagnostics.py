"""Unit tests for diagnostic checks and CLI wrappers."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import unity_bridge
from unity_bridge.commands import diagnostics
from unity_bridge.commands.diagnostics import DiagnosticCheck
from unity_bridge.core.bridge import CommandResult
from unity_bridge.core.output import OutputFormatter


def _bridge_dir(project_root: Path) -> Path:
    return project_root / "Assets" / "Scripts" / "Editor" / "ClaudeCodeBridge"


def _write_manifest(project_root: Path, content: dict[str, Any] | str) -> Path:
    bridge_dir = _bridge_dir(project_root)
    bridge_dir.mkdir(parents=True, exist_ok=True)
    manifest = bridge_dir / "bridge_manifest.json"
    if isinstance(content, str):
        manifest.write_text(content, encoding="utf-8")
    else:
        manifest.write_text(json.dumps(content), encoding="utf-8")
    return manifest


class TestDiagnosticCheckHelpers:

    def test_diagnostic_check_serializes_optional_suggestion(self) -> None:
        without_suggestion = DiagnosticCheck("Check", True, "ok").to_dict()
        with_suggestion = DiagnosticCheck("Check", False, "bad", "fix it").to_dict()

        assert without_suggestion == {"name": "Check", "passed": True, "message": "ok"}
        assert with_suggestion["suggestion"] == "fix it"

    def test_project_structure_reports_missing_and_present_assets(
        self, fake_project: Path, tmp_path: Path
    ) -> None:
        present = diagnostics._check_project_structure(fake_project)
        missing = diagnostics._check_project_structure(tmp_path / "not-a-project")

        assert present.passed is True
        assert "Assets/ directory found" in present.message
        assert missing.passed is False
        assert "Ensure you are in a Unity project" in (missing.suggestion or "")

    def test_bridge_installation_reports_key_file(self, fake_project: Path) -> None:
        missing = diagnostics._check_bridge_installed(fake_project)
        bridge_dir = _bridge_dir(fake_project)
        bridge_dir.mkdir(parents=True)
        (bridge_dir / "ClaudeUnityBridge.cs").write_text("// bridge", encoding="utf-8")

        present = diagnostics._check_bridge_installed(fake_project)

        assert missing.passed is False
        assert missing.suggestion == "Run `unity-bridge install` to install bridge files."
        assert present.passed is True
        assert str(bridge_dir) in present.message

    def test_bridge_version_reports_missing_valid_and_invalid_manifest(
        self, fake_project: Path
    ) -> None:
        missing = diagnostics._check_bridge_version(fake_project)
        _write_manifest(fake_project, {"version": "1.2.3"})
        valid = diagnostics._check_bridge_version(fake_project)
        _write_manifest(fake_project, "{not-json")
        invalid = diagnostics._check_bridge_version(fake_project)

        assert missing.passed is False
        assert "legacy install" in missing.message
        assert valid.passed is True
        assert valid.message == "v1.2.3"
        assert invalid.passed is False
        assert "Error reading manifest" in invalid.message

    def test_heartbeat_reports_fresh_and_missing(
        self, fake_project: Path, fake_heartbeat: Path
    ) -> None:
        fresh = diagnostics._check_heartbeat(fake_project)
        fake_heartbeat.unlink()
        missing = diagnostics._check_heartbeat(fake_project)

        assert fresh.passed is True
        assert "Fresh" in fresh.message
        assert missing.passed is False
        assert "Ensure Unity Editor is running" in (missing.suggestion or "")

    def test_directory_permissions_reports_missing_writable_and_not_writable(
        self, fake_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        missing = diagnostics._check_directory_permissions(tmp_path / "missing")
        writable = diagnostics._check_directory_permissions(fake_project)
        monkeypatch.setattr(diagnostics, "_is_writable", lambda _path: False)
        not_writable = diagnostics._check_directory_permissions(fake_project)

        assert missing.passed is False
        assert "commands/ missing" in missing.message
        assert writable.passed is True
        assert not_writable.passed is False
        assert "commands/ not writable" in not_writable.message
        assert "responses/ not writable" in not_writable.message

    def test_is_writable_returns_false_when_temp_file_creation_fails(
        self, fake_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fail_mkstemp(*_args: object, **_kwargs: object) -> tuple[int, str]:
            raise OSError("denied")

        monkeypatch.setattr("tempfile.mkstemp", fail_mkstemp)

        assert diagnostics._is_writable(fake_project / ".claude" / "unity" / "commands") is False

    def test_orphaned_files_counts_command_and_response_json(self, fake_project: Path) -> None:
        empty = diagnostics._check_orphaned_files(fake_project)
        commands_dir = fake_project / ".claude" / "unity" / "commands"
        responses_dir = fake_project / ".claude" / "unity" / "responses"
        (commands_dir / "a.json").write_text("{}", encoding="utf-8")
        (commands_dir / "ignore.tmp").write_text("{}", encoding="utf-8")
        (responses_dir / "b.json").write_text("{}", encoding="utf-8")

        stale = diagnostics._check_orphaned_files(fake_project)

        assert empty.passed is True
        assert empty.message == "No orphaned files"
        assert stale.passed is True
        assert stale.message == "2 stale file(s) found"
        assert stale.suggestion == "Run `unity-bridge clean` to remove them."

    def test_dependencies_report_present_and_missing_packages(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        present = diagnostics._check_dependencies()

        def fake_import_module(name: str) -> object:
            if name == "aiofiles":
                raise ImportError(name)
            return object()

        monkeypatch.setattr(diagnostics.importlib, "import_module", fake_import_module)
        missing = diagnostics._check_dependencies()

        assert present.passed is True
        assert missing.passed is False
        assert missing.message == "Missing: aiofiles"
        assert missing.suggestion == "Install with: pip install aiofiles"

    def test_unity_process_detects_windows_and_unix_processes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(diagnostics.sys, "platform", "win32")
        monkeypatch.setattr(
            diagnostics.subprocess,
            "check_output",
            lambda *_args, **_kwargs: "Unity.exe 1234 Console",
        )
        windows = diagnostics._check_unity_process()

        monkeypatch.setattr(diagnostics.sys, "platform", "linux")
        monkeypatch.setattr(
            diagnostics.subprocess,
            "check_output",
            lambda *_args, **_kwargs: "1234\n",
        )
        unix = diagnostics._check_unity_process()

        assert windows.passed is True
        assert windows.message == "Unity.exe is running"
        assert unix.passed is True
        assert unix.message == "Unity process found"

    def test_unity_process_reports_missing_process(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fail_check_output(*_args: object, **_kwargs: object) -> str:
            raise subprocess.SubprocessError("not found")

        monkeypatch.setattr(diagnostics.sys, "platform", "win32")
        monkeypatch.setattr(diagnostics.subprocess, "check_output", fail_check_output)

        result = diagnostics._check_unity_process()

        assert result.passed is False
        assert result.message == "Unity Editor process not detected"
        assert result.suggestion == "Start Unity Editor and open your project."

    def test_version_compatibility_reports_missing_match_mismatch_and_bad_manifest(
        self, fake_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        missing = diagnostics._check_version_compatibility(fake_project)
        monkeypatch.setattr(unity_bridge, "__version__", "2.4.0")
        _write_manifest(fake_project, {"version": "2.0.1"})
        compatible = diagnostics._check_version_compatibility(fake_project)
        _write_manifest(fake_project, {"version": "3.0.0"})
        mismatch = diagnostics._check_version_compatibility(fake_project)
        _write_manifest(fake_project, {"version": "not-semver"})
        invalid = diagnostics._check_version_compatibility(fake_project)

        assert missing.passed is False
        assert "No manifest" in missing.message
        assert compatible.passed is True
        assert "compatible" in compatible.message
        assert mismatch.passed is False
        assert "Major version mismatch" in mismatch.message
        assert invalid.passed is False
        assert "invalid literal" in invalid.message


class TestDiagnosticCommands:

    async def test_status_returns_health_monitor_result(
        self, fake_project: Path, fake_heartbeat: Path
    ) -> None:
        result = await diagnostics.status(fake_project)

        assert result.success is True
        assert result.data["healthy"] is True
        assert result.error is None

    async def test_doctor_returns_all_checks_and_overall_success(
        self, fake_project: Path, fake_heartbeat: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        bridge_dir = _bridge_dir(fake_project)
        bridge_dir.mkdir(parents=True)
        (bridge_dir / "ClaudeUnityBridge.cs").write_text("// bridge", encoding="utf-8")
        _write_manifest(fake_project, {"version": unity_bridge.__version__})
        monkeypatch.setattr(
            diagnostics,
            "_check_unity_process",
            lambda: DiagnosticCheck("Unity process", True, "Unity process found"),
        )

        result = await diagnostics.doctor(fake_project)

        assert result.success is True
        assert len(result.data) == 9
        assert {check["name"] for check in result.data} >= {
            "Project structure",
            "C# bridge installed",
            "Version compatibility",
        }

    async def test_profiler_sample_sends_requested_metric_flags(self, mock_bridge: Any) -> None:
        await diagnostics.profiler_sample(
            mock_bridge,
            memory=True,
            rendering=True,
            cpu=True,
            timeout=12,
        )

        mock_bridge.send_command_with_retry.assert_awaited_once_with(
            command_type="profiler-sample",
            parameters={
                "includeMemory": True,
                "includeRendering": True,
                "includeCPU": True,
            },
            timeout=12,
        )

    def test_status_cli_prints_status_result(
        self, fake_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        async def fake_status(_project_root: Path) -> CommandResult:
            return CommandResult(success=True, data={"healthy": True})

        monkeypatch.setattr(diagnostics, "status", fake_status)
        ctx = SimpleNamespace(
            obj=SimpleNamespace(project_root=fake_project, formatter=OutputFormatter())
        )

        diagnostics.status_cli(ctx)  # type: ignore[arg-type]

        parsed = json.loads(capsys.readouterr().out)
        assert parsed["success"] is True
        assert parsed["data"]["healthy"] is True

    def test_doctor_cli_prints_doctor_result(
        self, fake_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        async def fake_doctor(_project_root: Path) -> CommandResult:
            return CommandResult(success=True, data=[{"name": "Check", "passed": True}])

        monkeypatch.setattr(diagnostics, "doctor", fake_doctor)
        ctx = SimpleNamespace(
            obj=SimpleNamespace(project_root=fake_project, formatter=OutputFormatter())
        )

        diagnostics.doctor_cli(ctx)  # type: ignore[arg-type]

        parsed = json.loads(capsys.readouterr().out)
        assert parsed["data"][0]["name"] == "Check"

    def test_profiler_cli_dispatches_default_flags(
        self, mock_bridge: Any, capsys: pytest.CaptureFixture
    ) -> None:
        ctx = SimpleNamespace(obj=SimpleNamespace(bridge=mock_bridge, formatter=OutputFormatter()))

        diagnostics.profiler_cli(ctx)  # type: ignore[arg-type]

        parsed = json.loads(capsys.readouterr().out)
        assert parsed["success"] is True
        mock_bridge.send_command_with_retry.assert_awaited_once_with(
            command_type="profiler-sample",
            parameters={},
            timeout=30.0,
        )

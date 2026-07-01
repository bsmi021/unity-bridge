"""Tests for optional Unity Code Coverage bridge utility."""

from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from unity_bridge.commands.code_coverage import (
    CODE_COVERAGE_PACKAGE,
    VALID_OPERATIONS,
    coverage_app,
    code_coverage_operation,
)
from unity_bridge.core.output import OutputFormatter

ROOT = Path(__file__).resolve().parents[2]


def _call_args(mock: MagicMock) -> dict[str, Any]:
    call = mock.send_command_with_retry.call_args
    return call.kwargs if call.kwargs else dict(
        zip(["command_type", "parameters", "timeout"], call.args, strict=False)
    )


def _state(mock_bridge: MagicMock) -> SimpleNamespace:
    return SimpleNamespace(bridge=mock_bridge, formatter=OutputFormatter())


def _run_coverage(args: list[str], mock_bridge: MagicMock):
    return CliRunner().invoke(coverage_app, args, obj=_state(mock_bridge))


class TestCodeCoverageCommand:
    async def test_availability_dispatches(self, mock_bridge: MagicMock) -> None:
        await code_coverage_operation(mock_bridge, "availability")

        args = _call_args(mock_bridge)
        assert args["command_type"] == "code-coverage"
        assert args["parameters"] == {"operation": "availability"}

    async def test_install_dispatches_package_identifier(
        self, mock_bridge: MagicMock
    ) -> None:
        await code_coverage_operation(mock_bridge, "install")

        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "install",
            "identifier": CODE_COVERAGE_PACKAGE,
        }

    async def test_install_accepts_version(self, mock_bridge: MagicMock) -> None:
        await code_coverage_operation(mock_bridge, "install", version="1.3.0")

        assert _call_args(mock_bridge)["parameters"]["identifier"] == (
            f"{CODE_COVERAGE_PACKAGE}@1.3.0"
        )

    async def test_recording_operations_dispatch(self, mock_bridge: MagicMock) -> None:
        for operation in ("start-recording", "pause-recording", "resume-recording", "stop-recording"):
            await code_coverage_operation(mock_bridge, operation)
            assert _call_args(mock_bridge)["parameters"] == {"operation": operation}

    async def test_find_reports_dispatches_filters(self, mock_bridge: MagicMock) -> None:
        await code_coverage_operation(
            mock_bridge,
            "find-reports",
            report_path="CoverageResults",
            max_results=25,
        )

        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "find-reports",
            "reportPath": "CoverageResults",
            "maxResults": 25,
        }

    async def test_summarize_dispatches_report_path(self, mock_bridge: MagicMock) -> None:
        await code_coverage_operation(
            mock_bridge,
            "summarize",
            report_path="CoverageResults/Report/Summary.xml",
        )

        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "summarize",
            "reportPath": "CoverageResults/Report/Summary.xml",
        }

    async def test_timeout_defaults_to_long_coverage_timeout(
        self, mock_bridge: MagicMock
    ) -> None:
        await code_coverage_operation(mock_bridge, "availability")

        assert _call_args(mock_bridge)["timeout"] == 120.0

    async def test_invalid_operation_raises(self, mock_bridge: MagicMock) -> None:
        with pytest.raises(ValueError, match="Invalid code coverage operation"):
            await code_coverage_operation(mock_bridge, "bogus")

    def test_operation_set_is_complete(self) -> None:
        assert VALID_OPERATIONS == frozenset(
            {
                "availability",
                "install",
                "start-recording",
                "pause-recording",
                "resume-recording",
                "stop-recording",
                "find-reports",
                "summarize",
            }
        )


class TestCodeCoverageCli:
    def test_availability_cli(self, mock_bridge: MagicMock) -> None:
        result = _run_coverage(["availability"], mock_bridge)

        assert result.exit_code == 0
        assert _call_args(mock_bridge)["parameters"] == {"operation": "availability"}

    def test_install_cli_with_version(self, mock_bridge: MagicMock) -> None:
        result = _run_coverage(["install", "--version", "1.3.0"], mock_bridge)

        assert result.exit_code == 0
        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "install",
            "identifier": f"{CODE_COVERAGE_PACKAGE}@1.3.0",
        }

    @pytest.mark.parametrize(
        ("command", "operation"),
        [
            ("start", "start-recording"),
            ("pause", "pause-recording"),
            ("resume", "resume-recording"),
            ("stop", "stop-recording"),
        ],
    )
    def test_recording_cli_commands(
        self, mock_bridge: MagicMock, command: str, operation: str
    ) -> None:
        result = _run_coverage([command], mock_bridge)

        assert result.exit_code == 0
        assert _call_args(mock_bridge)["parameters"] == {"operation": operation}

    def test_find_reports_cli(self, mock_bridge: MagicMock) -> None:
        result = _run_coverage(
            ["find-reports", "--path", "CoverageResults", "--max-results", "25"],
            mock_bridge,
        )

        assert result.exit_code == 0
        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "find-reports",
            "reportPath": "CoverageResults",
            "maxResults": 25,
        }

    def test_summarize_cli_with_path(self, mock_bridge: MagicMock) -> None:
        result = _run_coverage(["summarize", "CoverageResults/Report/Summary.json"], mock_bridge)

        assert result.exit_code == 0
        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "summarize",
            "reportPath": "CoverageResults/Report/Summary.json",
        }


class TestCodeCoverageProtocol:
    def test_protocol_timeout_and_parallel_safety(self) -> None:
        from unity_bridge.core.protocol import (
            OPERATION_GATED_PARALLEL_SAFE,
            TIMEOUT_DEFAULTS,
            is_parallel_safe,
        )

        assert TIMEOUT_DEFAULTS["code-coverage"] == 120
        assert OPERATION_GATED_PARALLEL_SAFE["code-coverage"] == frozenset(
            {"availability", "find-reports", "summarize"}
        )
        assert is_parallel_safe("code-coverage", {"operation": "availability"}) is True
        assert is_parallel_safe("code-coverage", {"operation": "install"}) is False


class TestCodeCoverageCSharpContract:
    def test_handler_is_registered(self) -> None:
        registry = (ROOT / "ClaudeCodeBridge" / "BridgeCommandRegistry.cs").read_text(
            encoding="utf-8"
        )

        assert "new CodeCoverageCommandHandler()" in registry

    def test_handler_uses_reflection_for_optional_package(self) -> None:
        source = (ROOT / "ClaudeCodeBridge" / "CodeCoverageCommandHandler.cs").read_text(
            encoding="utf-8"
        )

        assert "using UnityEditor.TestTools.CodeCoverage" not in source
        assert "FindType(\"UnityEditor.TestTools.CodeCoverage.CodeCoverage\")" in source
        assert "PackageManagerInfo.FindForPackageName" in source
        assert "com.unity.testtools.codecoverage" in source

    def test_handler_qualifies_package_info_to_avoid_unityeditor_ambiguity(self) -> None:
        source = (ROOT / "ClaudeCodeBridge" / "CodeCoverageCommandHandler.cs").read_text(
            encoding="utf-8"
        )

        assert "using PackageManagerInfo = UnityEditor.PackageManager.PackageInfo;" in source
        assert "PackageManagerInfo.FindForPackageName" in source
        assert "PackageInfo info" not in source
        assert "static PackageInfo FindPackageInfo" not in source
        assert "IsPackageAvailable(PackageInfo" not in source

    def test_handler_supports_report_artifacts_without_package_api(self) -> None:
        source = (ROOT / "ClaudeCodeBridge" / "CodeCoverageCommandHandler.cs").read_text(
            encoding="utf-8"
        )

        assert '"find-reports"' in source
        assert '"summarize"' in source
        assert "ReadOpenCoverSummary" in source
        assert "Summary.json" in source

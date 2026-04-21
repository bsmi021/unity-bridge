"""Unit tests for commands/reports.py — NUnit + BuildReport extraction."""

from __future__ import annotations

from unity_bridge.commands.reports import extract_build_report, extract_test_report
from unity_bridge.core.bridge import CommandResult


# ---------------------------------------------------------------------------
# extract_test_report
# ---------------------------------------------------------------------------


class TestExtractTestReport:
    def test_returns_none_on_failure(self) -> None:
        result = CommandResult(success=False, data=None, command_id="x")
        assert extract_test_report(result) is None

    def test_returns_none_on_no_data(self) -> None:
        result = CommandResult(success=True, data=None, command_id="x")
        assert extract_test_report(result) is None

    def test_summary_fields(self) -> None:
        data = {
            "total": 10,
            "passed": 8,
            "failed": 1,
            "skipped": 1,
            "inconclusive": 0,
            "durationSeconds": 12.5,
            "resultState": "Failed",
            "testSuite": "Assembly-CSharp-Editor",
            "failures": [],
            "testCases": [],
        }
        report = extract_test_report(CommandResult(success=True, data=data, command_id="x"))
        assert report is not None
        assert report["total"] == 10
        assert report["passed"] == 8
        assert report["failed"] == 1
        assert report["duration_seconds"] == 12.5
        assert report["result_state"] == "Failed"
        assert report["test_suite"] == "Assembly-CSharp-Editor"

    def test_test_cases_are_normalized(self) -> None:
        data = {
            "total": 1,
            "passed": 1,
            "failed": 0,
            "skipped": 0,
            "inconclusive": 0,
            "durationSeconds": 0.1,
            "failures": [],
            "testCases": [
                {
                    "fullName": "CombatTests.TestDamage",
                    "status": "Passed",
                    "durationSeconds": 0.05,
                    "assembly": "Game.Tests",
                    "categories": "fast;combat",
                }
            ],
        }
        report = extract_test_report(CommandResult(success=True, data=data, command_id="x"))
        assert report is not None
        case = report["test_cases"][0]
        assert case["full_name"] == "CombatTests.TestDamage"
        assert case["status"] == "Passed"
        assert case["duration_seconds"] == 0.05
        assert case["assembly"] == "Game.Tests"
        assert case["categories"] == ["fast", "combat"]

    def test_categories_empty_when_missing(self) -> None:
        data = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "inconclusive": 0,
            "durationSeconds": 0,
            "testCases": [{"fullName": "A", "status": "Passed"}],
        }
        report = extract_test_report(CommandResult(success=True, data=data, command_id="x"))
        assert report is not None
        assert report["test_cases"][0]["categories"] == []

    def test_failures_are_normalized(self) -> None:
        data = {
            "total": 1,
            "passed": 0,
            "failed": 1,
            "skipped": 0,
            "inconclusive": 0,
            "durationSeconds": 0.2,
            "failures": [
                {
                    "testName": "Fixture.Test",
                    "errorMessage": "boom",
                    "stackTrace": "at ...",
                }
            ],
            "testCases": [],
        }
        report = extract_test_report(CommandResult(success=True, data=data, command_id="x"))
        assert report is not None
        fail = report["failures"][0]
        assert fail == {
            "test_name": "Fixture.Test",
            "error_message": "boom",
            "stack_trace": "at ...",
        }


# ---------------------------------------------------------------------------
# extract_build_report
# ---------------------------------------------------------------------------


class TestExtractBuildReport:
    def test_returns_none_without_summary(self) -> None:
        data = {"operation": "validate", "success": True}
        assert extract_build_report(CommandResult(success=True, data=data, command_id="x")) is None

    def test_returns_none_on_failure(self) -> None:
        assert extract_build_report(
            CommandResult(success=False, data={"summary": {"result": "Failed"}}, command_id="x")
        ) is None

    def test_summary_and_counts(self) -> None:
        data = {
            "summary": {
                "result": "Succeeded",
                "platform": "StandaloneWindows64",
                "platformGroup": "Standalone",
                "totalSizeBytes": 104857600,
                "totalSizeMb": 100.0,
                "totalTimeSeconds": 42.5,
                "buildStartedAt": "2026-04-20T10:00:00Z",
                "buildEndedAt": "2026-04-20T10:00:42Z",
                "outputPath": "Builds/Win/Game.exe",
                "buildGuid": "abc123",
            },
            "errorCount": 0,
            "warningCount": 3,
            "buildSteps": [],
            "largestAssets": [],
        }
        report = extract_build_report(CommandResult(success=True, data=data, command_id="x"))
        assert report is not None
        assert report["result"] == "Succeeded"
        assert report["platform"] == "StandaloneWindows64"
        assert report["total_size_mb"] == 100.0
        assert report["total_time_seconds"] == 42.5
        assert report["error_count"] == 0
        assert report["warning_count"] == 3
        assert report["build_guid"] == "abc123"

    def test_steps_and_assets(self) -> None:
        data = {
            "summary": {
                "result": "Succeeded",
                "platform": "StandaloneWindows64",
                "platformGroup": "Standalone",
                "totalSizeBytes": 0,
                "totalSizeMb": 0,
                "totalTimeSeconds": 0,
            },
            "buildSteps": [
                {
                    "name": "Compile scripts",
                    "durationSeconds": 12.0,
                    "depth": 0,
                    "messageCount": 2,
                }
            ],
            "largestAssets": [
                {
                    "assetPath": "Assets/Textures/Huge.png",
                    "sizeBytes": 52428800,
                    "sizeMb": 50.0,
                    "kind": "Texture2D",
                }
            ],
        }
        report = extract_build_report(CommandResult(success=True, data=data, command_id="x"))
        assert report is not None
        assert report["build_steps"][0]["name"] == "Compile scripts"
        assert report["build_steps"][0]["duration_seconds"] == 12.0
        assert report["largest_assets"][0]["asset_path"] == "Assets/Textures/Huge.png"
        assert report["largest_assets"][0]["size_mb"] == 50.0
        assert report["largest_assets"][0]["kind"] == "Texture2D"

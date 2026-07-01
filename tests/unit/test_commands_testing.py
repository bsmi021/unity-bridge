"""Unit tests for commands/testing.py — run_tests, compile_scripts."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

from typer.testing import CliRunner

from unity_bridge.commands.testing import cancel_tests, compile_scripts, run_tests, test_app
from unity_bridge.core.bridge import CommandResult
from unity_bridge.core.output import OutputFormatter


# ---------------------------------------------------------------------------
# run_tests
# ---------------------------------------------------------------------------


class TestRunTests:

    async def test_passes_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await run_tests(mock_bridge)
        mock_bridge.send_command_with_retry.assert_awaited_once()
        call_kwargs = mock_bridge.send_command_with_retry.call_args
        assert call_kwargs.kwargs.get("command_type") == "run-tests" or \
            call_kwargs[1].get("command_type") == "run-tests" or \
            (call_kwargs[0] and call_kwargs[0][0] == "run-tests")

    async def test_default_platform_is_editmode(self, mock_bridge: MagicMock) -> None:
        await run_tests(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        # Parameters should include testPlatform=EditMode
        params = _extract_parameters(call_args)
        assert params["testPlatform"] == "EditMode"

    async def test_custom_platform(self, mock_bridge: MagicMock) -> None:
        await run_tests(mock_bridge, platform="PlayMode")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["testPlatform"] == "PlayMode"

    async def test_filter_pattern_included_when_provided(
        self, mock_bridge: MagicMock
    ) -> None:
        await run_tests(mock_bridge, filter_pattern="CombatTests")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["testFilter"] == "CombatTests"

    async def test_filter_pattern_omitted_when_none(
        self, mock_bridge: MagicMock
    ) -> None:
        await run_tests(mock_bridge, filter_pattern=None)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "testFilter" not in params

    async def test_includes_explicit_test_names(self, mock_bridge: MagicMock) -> None:
        await run_tests(
            mock_bridge,
            test_names=[
                "Game.Tests.CombatTests.AttackDealsDamage",
                "Game.Tests.InventoryTests.AddsItem",
            ],
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["testNames"] == [
            "Game.Tests.CombatTests.AttackDealsDamage",
            "Game.Tests.InventoryTests.AddsItem",
        ]

    async def test_includes_group_category_and_assembly_selectors(
        self, mock_bridge: MagicMock
    ) -> None:
        await run_tests(
            mock_bridge,
            group_names=["^Game\\.Tests\\.Combat\\."],
            categories=["Smoke", "Combat"],
            assemblies=["Game.Editor.Tests"],
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["groupNames"] == ["^Game\\.Tests\\.Combat\\."]
        assert params["categoryNames"] == ["Smoke", "Combat"]
        assert params["assemblyNames"] == ["Game.Editor.Tests"]

    async def test_omits_empty_selector_lists(self, mock_bridge: MagicMock) -> None:
        await run_tests(
            mock_bridge,
            test_names=[],
            group_names=[],
            categories=[],
            assemblies=[],
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "testNames" not in params
        assert "groupNames" not in params
        assert "categoryNames" not in params
        assert "assemblyNames" not in params

    async def test_timeout_passed_through(self, mock_bridge: MagicMock) -> None:
        await run_tests(mock_bridge, timeout=600)
        call_args = mock_bridge.send_command_with_retry.call_args
        timeout = _extract_kwarg(call_args, "timeout")
        assert timeout == 600.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        expected = CommandResult(success=True, data={"passed": 5})
        mock_bridge.send_command_with_retry.return_value = expected
        result = await run_tests(mock_bridge)
        assert result.success is True
        assert result.data["passed"] == 5

    async def test_min_tests_fails_zero_test_success(
        self, mock_bridge: MagicMock
    ) -> None:
        mock_bridge.send_command_with_retry.return_value = CommandResult(
            success=True,
            data={"total": 0, "passed": 0, "failed": 0},
            command_id="cmd-zero",
            execution_time_ms=12,
        )

        result = await run_tests(mock_bridge, min_tests=1)

        assert result.success is False
        assert result.exit_code == 1
        assert result.command_id == "cmd-zero"
        assert result.data["total"] == 0
        assert "Expected at least 1 test" in result.error

    async def test_min_tests_passes_when_threshold_met(
        self, mock_bridge: MagicMock
    ) -> None:
        expected = CommandResult(success=True, data={"total": 2, "passed": 2})
        mock_bridge.send_command_with_retry.return_value = expected

        result = await run_tests(mock_bridge, min_tests=1)

        assert result is expected

    async def test_min_tests_does_not_rewrite_bridge_failure(
        self, mock_bridge: MagicMock
    ) -> None:
        expected = CommandResult(success=False, error="Unity failed", exit_code=4)
        mock_bridge.send_command_with_retry.return_value = expected

        result = await run_tests(mock_bridge, min_tests=1)

        assert result is expected


class TestRunTestsCli:
    def test_cli_passes_rich_selectors(self, mock_bridge: MagicMock) -> None:
        result = _run_test_cli(
            [
                "run",
                "--platform",
                "PlayMode",
                "--filter",
                "LegacyFilter",
                "--test-name",
                "Game.Tests.CombatTests.AttackDealsDamage",
                "--group",
                "^Game\\.Tests\\.Combat\\.",
                "--category",
                "Smoke",
                "--category",
                "Combat",
                "--assembly",
                "Game.Editor.Tests",
                "--timeout",
                "45",
                "--min-tests",
                "1",
            ],
            mock_bridge,
        )

        assert result.exit_code == 0
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["testPlatform"] == "PlayMode"
        assert params["testFilter"] == "LegacyFilter"
        assert params["testNames"] == ["Game.Tests.CombatTests.AttackDealsDamage"]
        assert params["groupNames"] == ["^Game\\.Tests\\.Combat\\."]
        assert params["categoryNames"] == ["Smoke", "Combat"]
        assert params["assemblyNames"] == ["Game.Editor.Tests"]
        assert _extract_kwarg(call_args, "timeout") == 45.0

    def test_cli_help_exposes_min_tests(self, mock_bridge: MagicMock) -> None:
        result = _run_test_cli(["run", "--help"], mock_bridge)

        assert result.exit_code == 0
        assert "--min-tests" in result.stdout


class TestCancelTests:
    async def test_cancel_tests_dispatches_target_command(
        self, mock_bridge: MagicMock
    ) -> None:
        result = await cancel_tests(mock_bridge, command_id="run-cmd", timeout=7)

        assert result.success is True
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "cancel-tests"
        assert _extract_parameters(call_args) == {"targetCommandId": "run-cmd"}
        assert _extract_kwarg(call_args, "timeout") == 7.0

    async def test_cancel_tests_allows_current_run_target(
        self, mock_bridge: MagicMock
    ) -> None:
        await cancel_tests(mock_bridge)

        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {}


class TestCancelTestsCli:
    def test_cancel_cli_dispatches_command_id(self, mock_bridge: MagicMock) -> None:
        result = _run_test_cli(
            ["cancel", "--command-id", "run-cmd", "--timeout", "9"],
            mock_bridge,
        )

        assert result.exit_code == 0
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "cancel-tests"
        assert _extract_parameters(call_args) == {"targetCommandId": "run-cmd"}
        assert _extract_kwarg(call_args, "timeout") == 9.0

    def test_cancel_help_is_exposed(self, mock_bridge: MagicMock) -> None:
        result = _run_test_cli(["cancel", "--help"], mock_bridge)

        assert result.exit_code == 0
        assert "--command-id" in result.stdout


class TestPreflightTests:
    async def test_preflight_reports_selected_tests(
        self, mock_bridge: MagicMock
    ) -> None:
        mod = _import_testing()
        mock_bridge.send_command_with_retry.return_value = CommandResult(
            success=True,
            data=_sample_discovered_tests(),
        )

        result = await mod.preflight_tests(
            mock_bridge,
            platform="EditMode",
            categories=["Smoke"],
            assemblies=["Game.Editor.Tests"],
            min_tests=1,
        )

        assert result.success is True
        assert result.data["readyToRun"] is True
        assert result.data["discoveredCount"] == 2
        assert result.data["selectedCount"] == 1
        assert result.data["sampleTests"] == ["Game.Tests.CombatTests.AttackDealsDamage"]
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["mode"] == "tests"
        assert params["testPlatform"] == "EditMode"

    async def test_preflight_applies_test_name_and_group_selectors(
        self, mock_bridge: MagicMock
    ) -> None:
        mod = _import_testing()
        mock_bridge.send_command_with_retry.return_value = CommandResult(
            success=True,
            data=_sample_discovered_tests(),
        )

        result = await mod.preflight_tests(
            mock_bridge,
            test_names=["Game.Tests.CombatTests.AttackDealsDamage"],
            group_names=["CombatTests"],
        )

        assert result.success is True
        assert result.data["selectedCount"] == 1

    async def test_preflight_fails_below_min_tests(self, mock_bridge: MagicMock) -> None:
        mod = _import_testing()
        mock_bridge.send_command_with_retry.return_value = CommandResult(
            success=True,
            data={"count": 0, "tests": []},
            command_id="cmd-list",
        )

        result = await mod.preflight_tests(mock_bridge, min_tests=1)

        assert result.success is False
        assert result.exit_code == 1
        assert result.command_id == "cmd-list"
        assert result.data["readyToRun"] is False
        assert "expected at least 1" in result.error

    async def test_preflight_invalid_group_regex_fails_without_bridge_call(
        self, mock_bridge: MagicMock
    ) -> None:
        mod = _import_testing()

        result = await mod.preflight_tests(mock_bridge, group_names=["["])

        assert result.success is False
        assert result.exit_code == 3
        mock_bridge.send_command_with_retry.assert_not_called()

    async def test_preflight_propagates_discovery_failure(
        self, mock_bridge: MagicMock
    ) -> None:
        mod = _import_testing()
        mock_bridge.send_command_with_retry.return_value = CommandResult(
            success=False,
            error="Cannot retrieve test tree while scripts are compiling.",
            exit_code=2,
        )

        result = await mod.preflight_tests(mock_bridge)

        assert result.success is False
        assert result.exit_code == 2
        assert result.data["checks"][0]["name"] == "test_discovery"


class TestPreflightCli:
    def test_preflight_cli_passes_selectors(self, mock_bridge: MagicMock) -> None:
        mock_bridge.send_command_with_retry.return_value = CommandResult(
            success=True,
            data=_sample_discovered_tests(),
        )

        result = _run_test_cli(
            [
                "preflight",
                "--platform",
                "EditMode",
                "--filter",
                "Combat",
                "--test-name",
                "Game.Tests.CombatTests.AttackDealsDamage",
                "--group",
                "CombatTests",
                "--category",
                "Smoke",
                "--assembly",
                "Game.Editor.Tests",
                "--min-tests",
                "1",
                "--timeout",
                "15",
            ],
            mock_bridge,
        )

        assert result.exit_code == 0
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["filter"] == "Combat"
        assert _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout") == 15.0
        assert '"ready_to_run": true' in result.stdout


class TestListAndCompileCli:
    def test_list_cli_passes_categories_mode(self, mock_bridge: MagicMock) -> None:
        result = _run_test_cli(
            ["list", "--platform", "PlayMode", "--filter", "Combat", "--categories"],
            mock_bridge,
        )

        assert result.exit_code == 0
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["mode"] == "categories"
        assert params["testPlatform"] == "PlayMode"
        assert params["filter"] == "Combat"

    def test_list_cli_passes_assemblies_mode(self, mock_bridge: MagicMock) -> None:
        result = _run_test_cli(["list", "--assemblies"], mock_bridge)

        assert result.exit_code == 0
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["mode"] == "assemblies"

    def test_compile_cli_passes_wait_and_timeout(self, mock_bridge: MagicMock) -> None:
        result = _run_test_cli(["compile", "--no-wait", "--timeout", "240"], mock_bridge)

        assert result.exit_code == 0
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["waitForCompletion"] is False
        assert _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout") == 240.0


class TestTestResultArtifacts:
    def test_reads_latest_artifact(self, tmp_path) -> None:
        mod = _import_testing()
        _write_artifact(tmp_path, "latest.json", command_id="cmd-latest", failed=1)

        result = mod.read_test_result_artifact(tmp_path)

        assert result.success is True
        assert result.data["commandId"] == "cmd-latest"
        assert result.data["result"]["failed"] == 1

    def test_reads_specific_command_artifact(self, tmp_path) -> None:
        mod = _import_testing()
        _write_artifact(tmp_path, "cmd-123.json", command_id="cmd-123", failed=0)

        result = mod.read_test_result_artifact(tmp_path, command_id="cmd-123")

        assert result.success is True
        assert result.data["commandId"] == "cmd-123"

    def test_missing_artifact_returns_structured_failure(self, tmp_path) -> None:
        mod = _import_testing()

        result = mod.read_test_result_artifact(tmp_path, command_id="missing")

        assert result.success is False
        assert result.exit_code == 2
        assert "No test result artifact found" in result.error

    def test_invalid_result_artifact_returns_structured_failure(self, tmp_path) -> None:
        mod = _import_testing()
        path = tmp_path / ".claude" / "unity" / "test-results" / "bad.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not-json}", encoding="utf-8")

        result = mod.read_test_result_artifact(tmp_path, command_id="bad")

        assert result.success is False
        assert result.exit_code == 5
        assert "Invalid test result artifact JSON" in result.error

    def test_failures_extracts_failure_records(self, tmp_path) -> None:
        mod = _import_testing()
        _write_artifact(tmp_path, "latest.json", command_id="cmd-fail", failed=1)

        result = mod.read_test_failures_artifact(tmp_path)

        assert result.success is True
        assert result.data["commandId"] == "cmd-fail"
        assert result.data["failed"] == 1
        assert result.data["failures"] == [
            {
                "testName": "Game.Tests.CombatTests.AttackFails",
                "errorMessage": "Expected damage",
                "stackTrace": "at CombatTests.cs:42",
            }
        ]

    def test_history_lists_command_artifacts_newest_first(self, tmp_path) -> None:
        mod = _import_testing()
        _write_artifact(
            tmp_path,
            "cmd-old.json",
            command_id="cmd-old",
            written_at="2026-06-25T10:00:00Z",
        )
        _write_artifact(
            tmp_path,
            "cmd-new.json",
            command_id="cmd-new",
            written_at="2026-06-26T10:00:00Z",
        )
        _write_artifact(tmp_path, "latest.json", command_id="cmd-new")

        result = mod.list_test_result_history(tmp_path)

        assert result.success is True
        assert [item["commandId"] for item in result.data["results"]] == ["cmd-new", "cmd-old"]

    def test_history_without_artifact_directory_returns_empty_result(self, tmp_path) -> None:
        mod = _import_testing()

        result = mod.list_test_result_history(tmp_path)

        assert result.success is True
        assert result.data == {"count": 0, "results": []}

    def test_history_skips_invalid_artifact_json(self, tmp_path) -> None:
        mod = _import_testing()
        path = tmp_path / ".claude" / "unity" / "test-results" / "bad.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not-json}", encoding="utf-8")

        result = mod.list_test_result_history(tmp_path)

        assert result.success is True
        assert result.data == {"count": 0, "results": []}


class TestTestProgressArtifacts:
    def test_reads_latest_progress_artifact(self, tmp_path) -> None:
        mod = _import_testing()
        _write_progress(tmp_path, "latest.json", command_id="cmd-progress", finished=3)

        result = mod.read_test_progress_artifact(tmp_path)

        assert result.success is True
        assert result.data["commandId"] == "cmd-progress"
        assert result.data["finished"] == 3

    def test_reads_specific_progress_artifact(self, tmp_path) -> None:
        mod = _import_testing()
        _write_progress(tmp_path, "cmd-progress.json", command_id="cmd-progress")

        result = mod.read_test_progress_artifact(tmp_path, command_id="cmd-progress")

        assert result.success is True
        assert result.data["state"] == "running"

    def test_missing_progress_artifact_returns_structured_failure(self, tmp_path) -> None:
        mod = _import_testing()

        result = mod.read_test_progress_artifact(tmp_path, command_id="missing")

        assert result.success is False
        assert result.exit_code == 2
        assert "No test progress artifact found" in result.error

    def test_invalid_progress_artifact_returns_structured_failure(self, tmp_path) -> None:
        mod = _import_testing()
        path = tmp_path / ".claude" / "unity" / "test-progress" / "bad.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not-json}", encoding="utf-8")

        result = mod.read_test_progress_artifact(tmp_path, command_id="bad")

        assert result.success is False
        assert result.exit_code == 5
        assert "Invalid test progress artifact JSON" in result.error


class TestTestProgressEvents:
    def test_reads_specific_event_log(self, tmp_path) -> None:
        mod = _import_testing()
        _write_progress_events(
            tmp_path,
            "cmd-progress",
            [
                {"state": "started", "testName": ""},
                {"state": "running", "testName": "Game.Tests.A"},
            ],
        )

        result = mod.read_test_progress_events(tmp_path, command_id="cmd-progress")

        assert result.success is True
        assert result.data["commandId"] == "cmd-progress"
        assert result.data["count"] == 2
        assert result.data["events"][1]["testName"] == "Game.Tests.A"

    def test_reads_latest_event_log_via_progress_artifact(self, tmp_path) -> None:
        mod = _import_testing()
        _write_progress(tmp_path, "latest.json", command_id="cmd-progress")
        _write_progress_events(tmp_path, "cmd-progress", [{"state": "finished"}])

        result = mod.read_test_progress_events(tmp_path)

        assert result.success is True
        assert result.data["commandId"] == "cmd-progress"
        assert result.data["events"] == [{"state": "finished"}]

    def test_event_log_respects_max_events(self, tmp_path) -> None:
        mod = _import_testing()
        _write_progress_events(
            tmp_path,
            "cmd-progress",
            [{"state": "one"}, {"state": "two"}, {"state": "three"}],
        )

        result = mod.read_test_progress_events(
            tmp_path,
            command_id="cmd-progress",
            max_events=2,
        )

        assert [event["state"] for event in result.data["events"]] == ["one", "two"]

    def test_event_log_skips_blank_lines(self, tmp_path) -> None:
        mod = _import_testing()
        path = tmp_path / ".claude" / "unity" / "test-progress" / "cmd-progress.events.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('\n{"state": "started"}\n', encoding="utf-8")

        result = mod.read_test_progress_events(tmp_path, command_id="cmd-progress")

        assert result.success is True
        assert result.data["events"] == [{"state": "started"}]

    def test_missing_event_log_returns_structured_failure(self, tmp_path) -> None:
        mod = _import_testing()

        result = mod.read_test_progress_events(tmp_path, command_id="missing")

        assert result.success is False
        assert result.exit_code == 2
        assert "No test progress event log found" in result.error

    def test_latest_event_log_without_command_id_returns_structured_failure(
        self, tmp_path
    ) -> None:
        mod = _import_testing()
        path = tmp_path / ".claude" / "unity" / "test-progress" / "latest.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"state": "running"}), encoding="utf-8")

        result = mod.read_test_progress_events(tmp_path)

        assert result.success is False
        assert result.exit_code == 2
        assert "No test progress command id was available" in result.error

    def test_invalid_event_log_returns_structured_failure(self, tmp_path) -> None:
        mod = _import_testing()
        path = tmp_path / ".claude" / "unity" / "test-progress" / "cmd.events.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not-json}\n", encoding="utf-8")

        result = mod.read_test_progress_events(tmp_path, command_id="cmd")

        assert result.success is False
        assert result.exit_code == 5
        assert "Invalid test progress event JSON" in result.error


class TestRerunFailedTests:
    async def test_reruns_failed_test_names_from_latest_artifact(
        self, tmp_path, mock_bridge: MagicMock
    ) -> None:
        mod = _import_testing()
        _write_artifact(tmp_path, "latest.json", command_id="cmd-fail", failed=1)

        result = await mod.rerun_failed_tests(mock_bridge, tmp_path)

        assert result.success is True
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["testNames"] == ["Game.Tests.CombatTests.AttackFails"]
        assert params["testPlatform"] == "EditMode"

    async def test_rerun_failed_deduplicates_and_omits_blank_names(
        self, tmp_path, mock_bridge: MagicMock
    ) -> None:
        mod = _import_testing()
        _write_artifact(
            tmp_path,
            "cmd-fail.json",
            command_id="cmd-fail",
            failures=[
                {"testName": "Game.Tests.A.Fails"},
                {"testName": ""},
                {"testName": "Game.Tests.A.Fails"},
                {"testName": "Game.Tests.B.Fails"},
            ],
        )

        await mod.rerun_failed_tests(mock_bridge, tmp_path, command_id="cmd-fail")

        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["testNames"] == ["Game.Tests.A.Fails", "Game.Tests.B.Fails"]

    async def test_rerun_failed_noops_without_failures(
        self, tmp_path, mock_bridge: MagicMock
    ) -> None:
        mod = _import_testing()
        _write_artifact(tmp_path, "latest.json", command_id="cmd-pass", failed=0)

        result = await mod.rerun_failed_tests(mock_bridge, tmp_path)

        assert result.success is True
        assert result.data == {
            "commandId": "cmd-pass",
            "rerunCount": 0,
            "testNames": [],
            "message": "No failed tests found to rerun.",
        }
        mock_bridge.send_command_with_retry.assert_not_called()

    async def test_rerun_failed_propagates_missing_artifact(
        self, tmp_path, mock_bridge: MagicMock
    ) -> None:
        mod = _import_testing()

        result = await mod.rerun_failed_tests(mock_bridge, tmp_path, command_id="missing")

        assert result.success is False
        assert result.exit_code == 2
        mock_bridge.send_command_with_retry.assert_not_called()


class TestTestResultArtifactCli:
    def test_results_cli_reads_latest_from_project_root(
        self, tmp_path, mock_bridge: MagicMock
    ) -> None:
        _write_artifact(tmp_path, "latest.json", command_id="cmd-cli")

        result = _run_test_cli(["results"], mock_bridge, project_root=tmp_path)

        assert result.exit_code == 0
        assert '"command_id": "cmd-cli"' in result.stdout

    def test_failures_cli_reads_specific_command(
        self, tmp_path, mock_bridge: MagicMock
    ) -> None:
        _write_artifact(tmp_path, "cmd-fail.json", command_id="cmd-fail", failed=1)

        result = _run_test_cli(
            ["failures", "--command-id", "cmd-fail"],
            mock_bridge,
            project_root=tmp_path,
        )

        assert result.exit_code == 0
        assert "AttackFails" in result.stdout

    def test_history_cli_lists_recent_results(self, tmp_path, mock_bridge: MagicMock) -> None:
        _write_artifact(tmp_path, "cmd-one.json", command_id="cmd-one")

        result = _run_test_cli(["history"], mock_bridge, project_root=tmp_path)

        assert result.exit_code == 0
        assert '"count": 1' in result.stdout

    def test_progress_cli_reads_latest_from_project_root(
        self, tmp_path, mock_bridge: MagicMock
    ) -> None:
        _write_progress(tmp_path, "latest.json", command_id="cmd-progress", finished=2)

        result = _run_test_cli(["progress"], mock_bridge, project_root=tmp_path)

        assert result.exit_code == 0
        assert '"command_id": "cmd-progress"' in result.stdout
        assert '"finished": 2' in result.stdout

    def test_events_cli_reads_specific_event_log(
        self, tmp_path, mock_bridge: MagicMock
    ) -> None:
        _write_progress_events(tmp_path, "cmd-progress", [{"state": "started"}])

        result = _run_test_cli(
            ["events", "--command-id", "cmd-progress", "--max-events", "1"],
            mock_bridge,
            project_root=tmp_path,
        )

        assert result.exit_code == 0
        assert '"command_id": "cmd-progress"' in result.stdout
        assert '"count": 1' in result.stdout

    def test_rerun_failed_cli_dispatches_specific_artifact(
        self, tmp_path, mock_bridge: MagicMock
    ) -> None:
        _write_artifact(tmp_path, "cmd-fail.json", command_id="cmd-fail", failed=1)

        result = _run_test_cli(
            [
                "rerun-failed",
                "--command-id",
                "cmd-fail",
                "--platform",
                "PlayMode",
                "--timeout",
                "45",
            ],
            mock_bridge,
            project_root=tmp_path,
        )

        assert result.exit_code == 0
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["testNames"] == ["Game.Tests.CombatTests.AttackFails"]
        assert params["testPlatform"] == "PlayMode"
        assert _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout") == 45.0


class TestRunTestsBridgeSource:
    def test_csharp_handler_maps_rich_selectors_to_unity_filter(self) -> None:
        source = (
            _repo_root()
            .joinpath("ClaudeCodeBridge", "RunTestsCommandHandler.cs")
            .read_text(encoding="utf-8")
        )

        assert "filter.testNames = MergeSelectors" in source
        assert "filter.groupNames = NonEmptyArray(parameters.groupNames)" in source
        assert "filter.categoryNames = NonEmptyArray(parameters.categoryNames)" in source
        assert "filter.assemblyNames = NonEmptyArray(parameters.assemblyNames)" in source

    def test_csharp_models_include_rich_selector_fields(self) -> None:
        source = (
            _repo_root()
            .joinpath("ClaudeCodeBridge", "BridgeModels.cs")
            .read_text(encoding="utf-8")
        )

        assert "public string[] testNames;" in source
        assert "public string[] groupNames;" in source
        assert "public string[] categoryNames;" in source
        assert "public string[] assemblyNames;" in source

    def test_csharp_reporter_writes_durable_test_artifacts(self) -> None:
        source = (
            _repo_root()
            .joinpath("ClaudeCodeBridge", "BridgeTestRunReporter.cs")
            .read_text(encoding="utf-8")
        )

        assert "WriteTestResultArtifact(commandId, parsed)" in source
        assert "test-results" in source
        assert "latest.json" in source
        assert "BridgeOperationLedger.WriteAtomic" in source

    def test_csharp_reporter_writes_progress_artifacts(self) -> None:
        source = (
            _repo_root()
            .joinpath("ClaudeCodeBridge", "BridgeTestRunReporter.cs")
            .read_text(encoding="utf-8")
        )

        assert "WriteTestProgress(commandId, \"started\"" in source
        assert "WriteTestProgress(commandId, \"running\"" in source
        assert "WriteTestProgress(commandId, \"finished\"" in source
        assert "test-progress" in source
        assert "TestProgressArtifact" in source
        assert "TestProgressEvent" in source
        assert ".events.jsonl" in source

    def test_csharp_cancel_handler_is_registered(self) -> None:
        source = (
            _repo_root()
            .joinpath("ClaudeCodeBridge", "BridgeCommandRegistry.cs")
            .read_text(encoding="utf-8")
        )

        assert "registerHandler(new CancelTestsCommandHandler())" in source

    def test_csharp_cancel_handler_calls_reporter_cancel(self) -> None:
        source = (
            _repo_root()
            .joinpath("ClaudeCodeBridge", "CancelTestsCommandHandler.cs")
            .read_text(encoding="utf-8")
        )

        assert 'public string CommandType => "cancel-tests"' in source
        assert "BridgeTestRunReporter.CancelRun" in source
        assert "targetCommandId" in source

    def test_csharp_reporter_persists_run_guid_and_cancel_progress(self) -> None:
        source = (
            _repo_root()
            .joinpath("ClaudeCodeBridge", "BridgeTestRunReporter.cs")
            .read_text(encoding="utf-8")
        )

        assert "RunGuidKey" in source
        assert "SessionState.SetString(RunGuidKey" in source
        assert "TestRunnerApi.CancelTestRun(runGuid)" in source
        assert 'WriteTestProgress(commandId, "cancel_requested"' in source


# ---------------------------------------------------------------------------
# compile_scripts
# ---------------------------------------------------------------------------


class TestCompileScripts:

    async def test_passes_compile_command(self, mock_bridge: MagicMock) -> None:
        await compile_scripts(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        cmd_type = _extract_command_type(call_args)
        assert cmd_type == "compile"

    async def test_wait_parameter_default_true(self, mock_bridge: MagicMock) -> None:
        await compile_scripts(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["waitForCompletion"] is True

    async def test_wait_parameter_false(self, mock_bridge: MagicMock) -> None:
        await compile_scripts(mock_bridge, wait=False)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["waitForCompletion"] is False

    async def test_timeout_passed(self, mock_bridge: MagicMock) -> None:
        await compile_scripts(mock_bridge, timeout=240)
        call_args = mock_bridge.send_command_with_retry.call_args
        timeout = _extract_kwarg(call_args, "timeout")
        assert timeout == 240.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _import_testing():
    from unity_bridge.commands import testing

    return testing


def _extract_parameters(call_args: Any) -> dict:
    """Extract the 'parameters' kwarg from a mock call."""
    if call_args.kwargs.get("parameters") is not None:
        return call_args.kwargs["parameters"]
    # Positional: send_command_with_retry(command_type, parameters, ...)
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


def _run_test_cli(args: list[str], mock_bridge: MagicMock, project_root=None):
    return CliRunner().invoke(test_app, args, obj=_state(mock_bridge, project_root))


def _state(mock_bridge: MagicMock, project_root=None):
    return type(
        "State",
        (),
        {
            "bridge": mock_bridge,
            "formatter": OutputFormatter(),
            "project_root": project_root,
        },
    )()


def _repo_root():
    from pathlib import Path

    return Path(__file__).resolve().parents[2]


def _write_artifact(
    project_root,
    filename: str,
    command_id: str,
    failed: int = 0,
    written_at: str = "2026-06-26T10:00:00Z",
    failures: list[dict[str, str]] | None = None,
) -> None:
    path = project_root / ".claude" / "unity" / "test-results" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    failure_records = failures
    if failure_records is None:
        failure_records = []
    if failed and not failure_records:
        failure_records.append(
            {
                "testName": "Game.Tests.CombatTests.AttackFails",
                "errorMessage": "Expected damage",
                "stackTrace": "at CombatTests.cs:42",
            }
        )
    payload = {
        "commandId": command_id,
        "writtenAt": written_at,
        "result": {
            "total": 1,
            "passed": 0 if failed else 1,
            "failed": failed,
            "failures": failure_records,
            "testCases": [],
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_progress(
    project_root,
    filename: str,
    command_id: str,
    state: str = "running",
    finished: int = 0,
) -> None:
    path = project_root / ".claude" / "unity" / "test-progress" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "commandId": command_id,
        "writtenAt": "2026-06-26T10:00:00Z",
        "state": state,
        "currentTest": "Game.Tests.CombatTests.Attack",
        "started": 3,
        "finished": finished,
        "passed": finished,
        "failed": 0,
        "skipped": 0,
        "inconclusive": 0,
        "durationSeconds": 1.25,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_progress_events(project_root, command_id: str, events: list[dict[str, str]]) -> None:
    path = project_root / ".claude" / "unity" / "test-progress" / f"{command_id}.events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "".join(f"{json.dumps(event)}\n" for event in events)
    path.write_text(content, encoding="utf-8")


def _sample_discovered_tests() -> dict:
    return {
        "count": 2,
        "tests": [
            {
                "fullName": "Game.Tests.CombatTests.AttackDealsDamage",
                "assembly": "Game.Editor.Tests",
                "categories": ["Smoke", "Combat"],
            },
            {
                "fullName": "Game.Tests.InventoryTests.AddsItem",
                "assembly": "Game.Editor.Tests",
                "categories": ["Inventory"],
            },
        ],
    }

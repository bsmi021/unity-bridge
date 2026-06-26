"""Unit tests for commands/testing.py — run_tests, compile_scripts."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

from typer.testing import CliRunner

from unity_bridge.commands.testing import compile_scripts, run_tests, test_app
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


class TestRunTestsSchema:
    def test_schema_exposes_rich_selectors(self) -> None:
        from unity_bridge.mcp.schemas import run_tests as run_tests_schema

        schema = run_tests_schema()
        properties = schema["properties"]
        assert properties["testNames"]["type"] == "array"
        assert properties["groupNames"]["type"] == "array"
        assert properties["categoryNames"]["type"] == "array"
        assert properties["assemblyNames"]["type"] == "array"


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
) -> None:
    path = project_root / ".claude" / "unity" / "test-results" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    failures = []
    if failed:
        failures.append(
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
            "failures": failures,
            "testCases": [],
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")

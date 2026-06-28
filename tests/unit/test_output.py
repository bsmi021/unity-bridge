"""Unit tests for core/output.py — OutputFormatter and print_result."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from unity_bridge.core.bridge import CommandResult
from unity_bridge.core.output import (
    OutputFormatter,
    format_console_logs,
    format_diagnostics,
    format_hierarchy,
    format_snapshot_diff,
    format_test_results,
    print_result,
)


# ---------------------------------------------------------------------------
# OutputFormatter construction
# ---------------------------------------------------------------------------


class TestOutputFormatterInit:

    def test_default_json_format(self) -> None:
        fmt = OutputFormatter()
        assert fmt.format == "json"
        assert fmt.color is True

    def test_custom_format(self) -> None:
        fmt = OutputFormatter(format="pretty", color=False)
        assert fmt.format == "pretty"
        assert fmt.color is False

    def test_human_format(self) -> None:
        fmt = OutputFormatter(format="human")
        assert fmt.format == "human"


# ---------------------------------------------------------------------------
# JSON output format
# ---------------------------------------------------------------------------


class TestJsonOutput:

    def test_compact_json_output(self) -> None:
        fmt = OutputFormatter(format="json")
        result = CommandResult(success=True, data={"some_key": "value"})
        output = fmt.format_result(result)
        parsed = json.loads(output)
        assert parsed["success"] is True

    def test_pretty_json_indented(self) -> None:
        fmt = OutputFormatter(format="pretty")
        result = CommandResult(success=True, data={"key": "val"})
        output = fmt.format_result(result)
        assert "\n" in output  # indented
        parsed = json.loads(output)
        assert parsed["success"] is True

    def test_output_is_valid_json(self) -> None:
        fmt = OutputFormatter(format="json")
        result = CommandResult(
            success=True, data={"count": 5, "items": [1, 2, 3]}, command_id="abc"
        )
        output = fmt.format_result(result)
        parsed = json.loads(output)
        assert parsed["success"] is True
        assert parsed["data"]["count"] == 5

    def test_snake_case_keys_in_data(self) -> None:
        """camelCase data should be converted to snake_case in output."""
        fmt = OutputFormatter(format="json")
        result = CommandResult(
            success=True,
            data={"testName": "Foo", "isPlaying": True, "nestedItems": [{"childName": "Bar"}]},
        )
        output = fmt.format_result(result)
        parsed = json.loads(output)
        # Keys in data should be snake_case
        assert "test_name" in parsed["data"]
        assert "is_playing" in parsed["data"]
        assert parsed["data"]["nested_items"][0]["child_name"] == "Bar"

    def test_result_metadata_is_emitted_when_present(self) -> None:
        fmt = OutputFormatter(format="json")
        result = CommandResult(
            success=True,
            data={"ok": True},
            command_id="cmd-1",
            execution_time_ms=42,
            exit_code=3,
            cached=True,
        )

        output = fmt.format_result(result)
        parsed = json.loads(output)

        assert parsed["command_id"] == "cmd-1"
        assert parsed["execution_time_ms"] == 42
        assert parsed["exit_code"] == 3
        assert parsed["cached"] is True


# ---------------------------------------------------------------------------
# Success / error formatting
# ---------------------------------------------------------------------------


class TestFormatterMethods:

    def test_success_json(self) -> None:
        fmt = OutputFormatter(format="json")
        output = fmt.success({"count": 5})
        parsed = json.loads(output)
        assert parsed["success"] is True

    def test_error_json(self) -> None:
        fmt = OutputFormatter(format="json")
        output = fmt.error("Something went wrong")
        parsed = json.loads(output)
        assert parsed["success"] is False
        assert "Something went wrong" in parsed["error"]

    def test_error_pretty(self) -> None:
        fmt = OutputFormatter(format="pretty")
        output = fmt.error("Bad request", details={"code": 400, "bridgeStatus": "offline"})
        parsed = json.loads(output)
        assert parsed["success"] is False
        assert parsed["details"]["bridge_status"] == "offline"

    def test_error_human(self) -> None:
        fmt = OutputFormatter(format="human", color=False)
        output = fmt.error("Failure message")
        assert "ERROR:" in output
        assert "Failure message" in output

    def test_error_human_includes_details_without_json(self) -> None:
        fmt = OutputFormatter(format="human", color=False)
        output = fmt.error("Failure message", details={"path": "Assets/Test.cs", "line": 12})

        assert "ERROR: Failure message" in output
        assert "path: Assets/Test.cs" in output
        assert "line: 12" in output

    def test_human_format_without_formatter_falls_back_to_json(self) -> None:
        fmt = OutputFormatter(format="human", color=False)
        result = CommandResult(success=True, data={"bridgeReady": True})

        output = fmt.format_result(result)
        parsed = json.loads(output)

        assert parsed["data"]["bridge_ready"] is True

    def test_success_with_human_formatter(self) -> None:
        fmt = OutputFormatter(format="human")

        def custom_fn(data, color):
            return f"Found {data['count']} items"

        output = fmt.success({"count": 3}, human_formatter=custom_fn)
        assert "3" in output


# ---------------------------------------------------------------------------
# print_result
# ---------------------------------------------------------------------------


class TestPrintResult:

    def test_success_prints_to_stdout(self, capsys: pytest.CaptureFixture) -> None:
        result = CommandResult(success=True, data={"key": "val"})
        fmt = OutputFormatter(format="json")
        # exit_code=0 means no SystemExit raised
        print_result(result, fmt)
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["success"] is True

    def test_error_exits_nonzero(self) -> None:
        result = CommandResult(success=False, error="fail", exit_code=1)
        fmt = OutputFormatter(format="json")
        with pytest.raises(SystemExit) as exc_info:
            print_result(result, fmt)
        assert exc_info.value.code == 1

    def test_exit_code_2_for_not_found(self) -> None:
        result = CommandResult(success=False, error="not found", exit_code=2)
        fmt = OutputFormatter(format="json")
        with pytest.raises(SystemExit) as exc_info:
            print_result(result, fmt)
        assert exc_info.value.code == 2

    def test_success_does_not_raise(self, capsys: pytest.CaptureFixture) -> None:
        """Successful results with exit_code=0 should not raise SystemExit."""
        result = CommandResult(success=True, data={"ok": True}, exit_code=0)
        fmt = OutputFormatter(format="json")
        print_result(result, fmt)  # should not raise

    def test_human_formatter_dispatched(self, capsys: pytest.CaptureFixture) -> None:
        result = CommandResult(success=True, data={"items": [1, 2]})
        fmt = OutputFormatter(format="human")
        human_fn = MagicMock(return_value="Human output")
        print_result(result, fmt, human_formatter=human_fn)
        human_fn.assert_called_once()

    def test_human_error_prints_to_stderr(self, capsys: pytest.CaptureFixture) -> None:
        result = CommandResult(success=False, error="fail", exit_code=1)
        fmt = OutputFormatter(format="human", color=False)

        with pytest.raises(SystemExit) as exc_info:
            print_result(result, fmt)

        captured = capsys.readouterr()
        assert exc_info.value.code == 1
        assert captured.out == ""
        assert '"error": "fail"' in captured.err


# ---------------------------------------------------------------------------
# Human formatters
# ---------------------------------------------------------------------------


class TestHumanFormatters:

    def test_format_test_results_handles_statuses_and_summary(self) -> None:
        data = {
            "results": [
                {"testName": "Passes", "result": "Passed", "duration": 0.012},
                {
                    "name": "Fails",
                    "status": "fail",
                    "duration": "bad-duration",
                    "message": "line1\nline2\nline3\nline4\nline5\nline6",
                },
                {"name": "Skipped", "status": "skipped", "duration": 1},
            ],
            "passed": 1,
            "failed": 1,
            "duration": 1.5,
        }

        output = format_test_results(data, color=False)

        assert "PASS  Passes (12ms)" in output
        assert "FAIL  Fails (0ms)" in output
        assert "SKIPPED  Skipped (1000ms)" in output
        assert "line5" in output
        assert "line6" not in output
        assert "Results: 1 passed, 1 failed (1500ms total)" in output

    def test_format_test_results_accepts_legacy_key_and_non_dict(self) -> None:
        output = format_test_results(
            {"testResults": [{"testName": "Legacy", "result": "pass", "duration": 0}]},
            color=False,
        )

        assert "PASS  Legacy (0ms)" in output
        assert format_test_results("raw output", color=False) == "raw output"

    def test_format_hierarchy_renders_tree_components_and_non_dict(self) -> None:
        data = {
            "sceneName": "Main",
            "children": [
                {
                    "name": "Player",
                    "components": ["Transform", {"type": "Health"}, {}],
                    "children": [{"name": "Camera"}],
                },
                {"name": "UI"},
            ],
        }

        output = format_hierarchy(data, color=False)

        assert "Scene: Main" in output
        assert "|-- Player [Transform, Health, ?]" in output
        assert "|   |__ Camera" in output
        assert "|__ UI" in output
        assert format_hierarchy(["raw"], color=False) == "['raw']"

    def test_format_hierarchy_accepts_scene_and_objects_aliases(self) -> None:
        output = format_hierarchy({"scene": "AliasScene", "objects": [{"name": "Root"}]}, color=False)

        assert "Scene: AliasScene" in output
        assert "|__ Root" in output

    def test_format_console_logs_handles_dict_list_and_log_types(self) -> None:
        data = {
            "logs": [
                {"logType": "Error", "message": "boom\nstack1\nstack2\nstack3\nstack4"},
                {"type": "Warning", "message": "careful"},
                {"type": "Exception", "message": "explode"},
                {"type": "Log", "message": "hello"},
            ]
        }

        output = format_console_logs(data, color=False)

        assert "[ERR] boom" in output
        assert "      stack3" in output
        assert "stack4" not in output
        assert "[WRN] careful" in output
        assert "[ERR] explode" in output
        assert "[LOG] hello" in output
        assert format_console_logs("raw", color=False) == "raw"

    def test_format_console_logs_accepts_entries_list_and_empty_message(self) -> None:
        output = format_console_logs(
            [{"type": "Log", "message": ""}, {"message": "default type"}],
            color=False,
        )

        assert "[LOG] " in output
        assert "[LOG] default type" in output

    def test_format_snapshot_diff_renders_all_sections_and_empty_state(self) -> None:
        data = {
            "added": ["Enemy", {"name": "Pickup"}],
            "removed": ["OldEnemy", {"name": "OldPickup"}],
            "modified": ["Player", {"name": "Hud"}],
        }

        output = format_snapshot_diff(data, color=False)

        assert "+ 2 added" in output
        assert "  + Enemy" in output
        assert "  + Pickup" in output
        assert "- 2 removed" in output
        assert "~ 2 modified" in output
        assert format_snapshot_diff({}, color=False) == "No differences found."
        assert format_snapshot_diff("raw", color=False) == "raw"

    def test_format_snapshot_diff_limits_each_section_to_twenty_items(self) -> None:
        data = {"added": [f"Item{i}" for i in range(25)]}

        output = format_snapshot_diff(data, color=False)

        assert "  + Item19" in output
        assert "  + Item20" not in output

    def test_format_diagnostics_handles_online_offline_and_uptime(self) -> None:
        online = {
            "healthy": True,
            "unityVersion": "6000.0",
            "activeScene": "Main",
            "uptimeSeconds": 3661,
            "heartbeatAgeSeconds": 0.25,
            "commandsProcessed": 7,
        }
        snake_case = {
            "healthy": True,
            "unity_version": "2022.3",
            "active_scene": "Menu",
            "uptime_seconds": 125,
            "heartbeat_age_seconds": 2.5,
            "commands_processed": 3,
        }

        assert "Unity 6000.0 | Scene: Main | Uptime: 1h 1m" in format_diagnostics(
            online, color=False
        )
        assert "Unity 2022.3 | Scene: Menu | Uptime: 2m 5s" in format_diagnostics(
            snake_case, color=False
        )
        assert "OFFLINE" in format_diagnostics({"healthy": False, "reason": "No heartbeat"}, False)
        assert "Unknown reason" in format_diagnostics({"healthy": False}, False)
        assert format_diagnostics("raw", color=False) == "raw"

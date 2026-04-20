"""Unit tests for core/output.py — OutputFormatter and print_result."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from unity_bridge.core.bridge import CommandResult
from unity_bridge.core.output import OutputFormatter, print_result


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
            success=True, data={"testName": "Foo", "isPlaying": True}
        )
        output = fmt.format_result(result)
        parsed = json.loads(output)
        # Keys in data should be snake_case
        assert "test_name" in parsed["data"]
        assert "is_playing" in parsed["data"]


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
        output = fmt.error("Bad request", details={"code": 400})
        parsed = json.loads(output)
        assert parsed["success"] is False

    def test_error_human(self) -> None:
        fmt = OutputFormatter(format="human", color=False)
        output = fmt.error("Failure message")
        assert "ERROR:" in output
        assert "Failure message" in output

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

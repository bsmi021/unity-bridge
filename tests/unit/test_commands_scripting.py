"""Unit tests for commands/scripting.py — script command."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from unity_bridge.core.bridge import CommandResult

ROOT = Path(__file__).resolve().parents[2]


def _import_scripting():
    from unity_bridge.commands import scripting

    return scripting


# ---------------------------------------------------------------------------
# script — expression execution
# ---------------------------------------------------------------------------


class TestScript:
    async def test_builds_correct_parameters(self, mock_bridge: MagicMock) -> None:
        scripting = _import_scripting()
        await scripting.execute_script(mock_bridge, expression="Debug.Log('hi')")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["expression"] == "Debug.Log('hi')"

    async def test_command_type_is_execute_script(self, mock_bridge: MagicMock) -> None:
        scripting = _import_scripting()
        await scripting.execute_script(mock_bridge, expression="1+1")
        call_args = mock_bridge.send_command_with_retry.call_args
        cmd_type = _extract_command_type(call_args)
        assert cmd_type == "execute-script"

    async def test_file_reads_content(
        self, mock_bridge: MagicMock, tmp_path: Path
    ) -> None:
        scripting = _import_scripting()
        script_file = tmp_path / "setup.cs"
        script_file.write_text(
            "var go = new GameObject(\"Test\");\ngo.transform.position = Vector3.up;",
            encoding="utf-8",
        )
        await scripting.execute_script(
            mock_bridge, expression=None, file=script_file
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert "new GameObject" in params["expression"]

    async def test_timeout_passed_through(self, mock_bridge: MagicMock) -> None:
        scripting = _import_scripting()
        await scripting.execute_script(
            mock_bridge, expression="1+1", timeout=60
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        timeout = _extract_kwarg(call_args, "timeout")
        assert timeout == 60.0 or timeout == 60

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        scripting = _import_scripting()
        expected = CommandResult(
            success=True,
            data={"result": "42", "resultType": "System.Int32"},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await scripting.execute_script(mock_bridge, expression="40+2")
        assert result.success is True
        assert result.data["result"] == "42"

    def test_csharp_handler_exists_and_is_registered(self) -> None:
        handler = ROOT / "ClaudeCodeBridge" / "ExecuteScriptCommandHandler.cs"
        registry = ROOT / "ClaudeCodeBridge" / "BridgeCommandRegistry.cs"

        assert handler.is_file()
        assert "CommandType => \"execute-script\"" in handler.read_text(encoding="utf-8")
        assert "new ExecuteScriptCommandHandler()" in registry.read_text(encoding="utf-8")


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

"""Unit tests for commands/input_system.py — Input System configuration."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.core.bridge import CommandResult


def _import_input():
    from unity_bridge.commands import input_system

    return input_system


class TestInputListActions:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_input()
        await mod.input_list_actions(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "input-system"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_input()
        await mod.input_list_actions(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "list-actions"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_input()
        await mod.input_list_actions(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 10.0


class TestInputGetActionMap:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_input()
        await mod.input_get_action_map(mock_bridge, "Assets/Input/Actions.inputactions")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "get-action-map"
        assert params["assetPath"] == "Assets/Input/Actions.inputactions"


class TestInputExport:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_input()
        await mod.input_export(mock_bridge, "Assets/Input/A.inputactions", "output.json")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "export"
        assert params["assetPath"] == "Assets/Input/A.inputactions"
        assert params["outputPath"] == "output.json"

    async def test_no_output_path_excludes_key(self, mock_bridge: MagicMock) -> None:
        mod = _import_input()
        await mod.input_export(mock_bridge, "Assets/Input/A.inputactions")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert "outputPath" not in params


class TestInputImport:
    async def test_sends_json_data(self, mock_bridge: MagicMock) -> None:
        mod = _import_input()
        await mod.input_import(mock_bridge, "Assets/Input/A.inputactions", json_data='{"maps":[]}')
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "import"
        assert params["json"] == '{"maps":[]}'

    async def test_sends_input_path(self, mock_bridge: MagicMock) -> None:
        mod = _import_input()
        await mod.input_import(
            mock_bridge, "Assets/Input/A.inputactions", input_path="input.json"
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["inputPath"] == "input.json"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_input()
        await mod.input_import(mock_bridge, "a", json_data="{}")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 15.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_input()
        expected = CommandResult(success=True, data={"operation": "import"})
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.input_import(mock_bridge, "a", json_data="{}")
        assert result.success is True


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

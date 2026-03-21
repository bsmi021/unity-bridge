"""Unit tests for commands/script_info.py — MonoScript inspection."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.core.bridge import CommandResult


def _import_script_info():
    from unity_bridge.commands import script_info

    return script_info


class TestScriptInfo:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_script_info()
        await mod.script_info(mock_bridge, "Assets/Scripts/Player.cs")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "script-info"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_script_info()
        await mod.script_info(mock_bridge, "Assets/Scripts/Player.cs")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "info"
        assert params["assetPath"] == "Assets/Scripts/Player.cs"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_script_info()
        await mod.script_info(mock_bridge, "a.cs")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 10.0


class TestScriptList:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_script_info()
        await mod.script_list(mock_bridge, filter_name="Player")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "list"
        assert params["filter"] == "Player"
        assert params["maxResults"] == 500

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_script_info()
        await mod.script_list(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 15.0

    async def test_no_filter_omits_key(self, mock_bridge: MagicMock) -> None:
        mod = _import_script_info()
        await mod.script_list(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert "filter" not in params


class TestScriptFindComponent:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_script_info()
        await mod.script_find_component(mock_bridge, "Player", "PlayerController")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "find-component"
        assert params["gameObjectPath"] == "Player"
        assert params["componentType"] == "PlayerController"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_script_info()
        await mod.script_find_component(mock_bridge, "Player", "Script")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 10.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_script_info()
        expected = CommandResult(
            success=True,
            data={"script": {"className": "PlayerController", "path": "Assets/Scripts/PC.cs"}},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.script_find_component(mock_bridge, "Player", "PlayerController")
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

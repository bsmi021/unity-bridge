"""Unit tests for commands/preset.py — preset management."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.core.bridge import CommandResult


def _import_preset():
    from unity_bridge.commands import preset

    return preset


class TestPresetCreate:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_preset()
        await mod.preset_create(mock_bridge, "Assets/Mat.mat", "Assets/Presets/Mat.preset")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "preset-operation"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_preset()
        await mod.preset_create(mock_bridge, "Assets/Mat.mat", "Assets/Presets/Mat.preset")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "create"
        assert params["sourcePath"] == "Assets/Mat.mat"
        assert params["outputPath"] == "Assets/Presets/Mat.preset"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_preset()
        await mod.preset_create(mock_bridge, "a", "b")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 15.0


class TestPresetApply:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_preset()
        await mod.preset_apply(mock_bridge, "Assets/P.preset", "Assets/T.mat")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "apply"
        assert params["presetPath"] == "Assets/P.preset"
        assert params["targetPath"] == "Assets/T.mat"


class TestPresetCanApply:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_preset()
        await mod.preset_can_apply(mock_bridge, "Assets/P.preset", "Assets/T.mat")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "can-apply"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_preset()
        await mod.preset_can_apply(mock_bridge, "a", "b")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 10.0


class TestPresetListDefaults:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_preset()
        await mod.preset_list_defaults(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "preset-operation"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_preset()
        await mod.preset_list_defaults(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "list-defaults"

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_preset()
        expected = CommandResult(success=True, data={"defaults": [], "message": "Found 0"})
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.preset_list_defaults(mock_bridge)
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

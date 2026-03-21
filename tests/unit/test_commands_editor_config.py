"""Unit tests for commands/editor_config.py — editor configuration operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.commands.editor_config import (
    editor_config_get,
    editor_config_set,
)


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


# ---------------------------------------------------------------------------
# editor-config get
# ---------------------------------------------------------------------------


class TestEditorConfigGet:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await editor_config_get(mock_bridge)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "editor-config"

    async def test_sends_get_operation(self, mock_bridge: MagicMock) -> None:
        await editor_config_get(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "get"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        await editor_config_get(mock_bridge)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 10.0

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await editor_config_get(failing_bridge)
        assert result.success is False


# ---------------------------------------------------------------------------
# editor-config set
# ---------------------------------------------------------------------------


class TestEditorConfigSet:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await editor_config_set(mock_bridge, "serializationMode", "ForceText")
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "editor-config"

    async def test_sends_set_operation(self, mock_bridge: MagicMock) -> None:
        await editor_config_set(mock_bridge, "serializationMode", "ForceText")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "set"
        assert params["key"] == "serializationMode"
        assert params["value"] == "ForceText"

    async def test_bool_value(self, mock_bridge: MagicMock) -> None:
        await editor_config_set(mock_bridge, "enterPlayModeOptionsEnabled", "true")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["value"] == "true"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        await editor_config_set(mock_bridge, "k", "v")
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 15.0

    async def test_custom_timeout(self, mock_bridge: MagicMock) -> None:
        await editor_config_set(mock_bridge, "k", "v", timeout=5.0)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 5.0

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await editor_config_set(failing_bridge, "k", "v")
        assert result.success is False


# ---------------------------------------------------------------------------
# Adversarial
# ---------------------------------------------------------------------------


class TestEditorConfigAdversarial:
    async def test_all_operations_use_send_command_with_retry(self, mock_bridge: MagicMock) -> None:
        await editor_config_get(mock_bridge)
        await editor_config_set(mock_bridge, "k", "v")
        assert mock_bridge.send_command_with_retry.call_count == 2
        assert mock_bridge.send_command.call_count == 0

    async def test_special_chars_in_value(self, mock_bridge: MagicMock) -> None:
        await editor_config_set(mock_bridge, "namespace", "BWS.Game.Core")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["value"] == "BWS.Game.Core"

"""Unit tests for commands/settings.py — player settings operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from unity_bridge.core.bridge import CommandResult


def _import_settings():
    from unity_bridge.commands import settings

    return settings


# ---------------------------------------------------------------------------
# get operation
# ---------------------------------------------------------------------------


class TestGetAll:
    async def test_builds_correct_parameters(self, mock_bridge: MagicMock) -> None:
        settings = _import_settings()
        await settings.player_settings_operation(mock_bridge, action="get")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "get"
        assert "key" not in params

    async def test_command_type(self, mock_bridge: MagicMock) -> None:
        settings = _import_settings()
        await settings.player_settings_operation(mock_bridge, action="get")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "player-settings-operation"


class TestGetSingle:
    async def test_includes_key(self, mock_bridge: MagicMock) -> None:
        settings = _import_settings()
        await settings.player_settings_operation(mock_bridge, action="get", key="companyName")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "get"
        assert params["key"] == "companyName"


# ---------------------------------------------------------------------------
# set operation
# ---------------------------------------------------------------------------


class TestSet:
    async def test_builds_correct_parameters(self, mock_bridge: MagicMock) -> None:
        settings = _import_settings()
        await settings.player_settings_operation(
            mock_bridge, action="set", key="companyName", value="NewCo"
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "set"
        assert params["key"] == "companyName"
        assert params["value"] == "NewCo"

    async def test_command_type(self, mock_bridge: MagicMock) -> None:
        settings = _import_settings()
        await settings.player_settings_operation(
            mock_bridge, action="set", key="productName", value="MyGame"
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "player-settings-operation"


# ---------------------------------------------------------------------------
# defines-list operation
# ---------------------------------------------------------------------------


class TestDefinesList:
    async def test_builds_correct_parameters(self, mock_bridge: MagicMock) -> None:
        settings = _import_settings()
        await settings.player_settings_operation(
            mock_bridge, action="defines-list", platform="Standalone"
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "defines-list"
        assert params["platform"] == "Standalone"

    async def test_platform_is_optional(self, mock_bridge: MagicMock) -> None:
        settings = _import_settings()
        await settings.player_settings_operation(mock_bridge, action="defines-list")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "defines-list"
        assert "platform" not in params


# ---------------------------------------------------------------------------
# defines-add operation
# ---------------------------------------------------------------------------


class TestDefinesAdd:
    async def test_builds_correct_parameters(self, mock_bridge: MagicMock) -> None:
        settings = _import_settings()
        await settings.player_settings_operation(
            mock_bridge, action="defines-add", symbol="MY_FEATURE", platform="Android"
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "defines-add"
        assert params["symbol"] == "MY_FEATURE"
        assert params["platform"] == "Android"


# ---------------------------------------------------------------------------
# defines-remove operation
# ---------------------------------------------------------------------------


class TestDefinesRemove:
    async def test_builds_correct_parameters(self, mock_bridge: MagicMock) -> None:
        settings = _import_settings()
        await settings.player_settings_operation(
            mock_bridge, action="defines-remove", symbol="DEBUG_MODE", platform="iOS"
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "defines-remove"
        assert params["symbol"] == "DEBUG_MODE"
        assert params["platform"] == "iOS"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    async def test_invalid_action_raises(self, mock_bridge: MagicMock) -> None:
        settings = _import_settings()
        with pytest.raises(ValueError, match="Invalid settings action"):
            await settings.player_settings_operation(mock_bridge, action="invalid")

    async def test_action_normalised(self, mock_bridge: MagicMock) -> None:
        settings = _import_settings()
        await settings.player_settings_operation(mock_bridge, action="  GET  ")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "get"


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------


class TestTimeout:
    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        settings = _import_settings()
        await settings.player_settings_operation(mock_bridge, action="get")
        call_args = mock_bridge.send_command_with_retry.call_args
        timeout = _extract_kwarg(call_args, "timeout")
        assert timeout == 15.0 or timeout == 15

    async def test_custom_timeout(self, mock_bridge: MagicMock) -> None:
        settings = _import_settings()
        await settings.player_settings_operation(mock_bridge, action="get", timeout=60)
        call_args = mock_bridge.send_command_with_retry.call_args
        timeout = _extract_kwarg(call_args, "timeout")
        assert timeout == 60.0 or timeout == 60


# ---------------------------------------------------------------------------
# Return value
# ---------------------------------------------------------------------------


class TestReturnValue:
    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        settings = _import_settings()
        expected = CommandResult(
            success=True,
            data={"operation": "get", "settings": {"companyName": "Test"}},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await settings.player_settings_operation(mock_bridge, action="get")
        assert result.success is True
        assert result.data["operation"] == "get"

    async def test_optional_params_excluded(self, mock_bridge: MagicMock) -> None:
        settings = _import_settings()
        await settings.player_settings_operation(mock_bridge, action="get")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert "key" not in params
        assert "value" not in params
        assert "symbol" not in params
        assert "platform" not in params


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

"""Unit tests for commands/quality_config.py — quality settings operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.commands.quality_config import (
    quality_get,
    quality_list,
    quality_set_level,
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
# quality list
# ---------------------------------------------------------------------------


class TestQualityList:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await quality_list(mock_bridge)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "quality-settings"

    async def test_sends_list_operation(self, mock_bridge: MagicMock) -> None:
        await quality_list(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "list"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        await quality_list(mock_bridge)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 10.0

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await quality_list(failing_bridge)
        assert result.success is False


# ---------------------------------------------------------------------------
# quality get
# ---------------------------------------------------------------------------


class TestQualityGet:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await quality_get(mock_bridge)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "quality-settings"

    async def test_sends_get_operation(self, mock_bridge: MagicMock) -> None:
        await quality_get(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "get"

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await quality_get(failing_bridge)
        assert result.success is False


# ---------------------------------------------------------------------------
# quality set-level
# ---------------------------------------------------------------------------


class TestQualitySetLevel:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await quality_set_level(mock_bridge, 2)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "quality-settings"

    async def test_sends_set_level_operation(self, mock_bridge: MagicMock) -> None:
        await quality_set_level(mock_bridge, 3)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "set-level"
        assert params["level"] == 3

    async def test_zero_level(self, mock_bridge: MagicMock) -> None:
        await quality_set_level(mock_bridge, 0)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["level"] == 0

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        await quality_set_level(mock_bridge, 0)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 15.0

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await quality_set_level(failing_bridge, 0)
        assert result.success is False


# ---------------------------------------------------------------------------
# Adversarial
# ---------------------------------------------------------------------------


class TestQualityAdversarial:
    async def test_all_operations_use_send_command_with_retry(self, mock_bridge: MagicMock) -> None:
        await quality_list(mock_bridge)
        await quality_get(mock_bridge)
        await quality_set_level(mock_bridge, 0)
        assert mock_bridge.send_command_with_retry.call_count == 3
        assert mock_bridge.send_command.call_count == 0

    async def test_negative_level_still_sent(self, mock_bridge: MagicMock) -> None:
        """Python side should not validate — let C# handle it."""
        await quality_set_level(mock_bridge, -1)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["level"] == -1

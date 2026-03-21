"""Unit tests for commands/time_settings.py — time settings operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from unity_bridge.core.bridge import CommandResult


def _import_mod():
    from unity_bridge.commands import time_settings

    return time_settings


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


class TestTimeGet:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.time_get(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "time-settings"

    async def test_sends_get_operation(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.time_get(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params == {"operation": "get"}

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.time_get(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 10.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        expected = CommandResult(
            success=True,
            data={
                "operation": "get",
                "fixedDeltaTime": 0.02,
                "timeScale": 1.0,
                "success": True,
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.time_get(mock_bridge)
        assert result.success is True
        assert result.data["fixedDeltaTime"] == pytest.approx(0.02)


# ---------------------------------------------------------------------------
# set
# ---------------------------------------------------------------------------


class TestTimeSet:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.time_set(mock_bridge, fixed_delta=0.02)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "time-settings"

    async def test_builds_fixed_delta_params(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.time_set(mock_bridge, fixed_delta=0.01)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "set"
        assert params["fixedDeltaTime"] == pytest.approx(0.01)
        assert params["setFixedDeltaTime"] is True

    async def test_builds_time_scale_params(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.time_set(mock_bridge, time_scale=0.5)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["timeScale"] == pytest.approx(0.5)
        assert params["setTimeScale"] is True

    async def test_omits_unset_params(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.time_set(mock_bridge, fixed_delta=0.02)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert "timeScale" not in params
        assert "maximumDeltaTime" not in params

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.time_set(mock_bridge, time_scale=1.0)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 15.0


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

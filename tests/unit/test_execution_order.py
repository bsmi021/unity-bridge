"""Unit tests for commands/execution_order.py — script execution order."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.core.bridge import CommandResult


def _import_mod():
    from unity_bridge.commands import execution_order

    return execution_order


# ---------------------------------------------------------------------------
# get_execution_order
# ---------------------------------------------------------------------------


class TestGetExecutionOrder:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.get_execution_order(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "script-execution-order"

    async def test_sends_get_operation(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.get_execution_order(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "get"

    async def test_non_default_only(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.get_execution_order(mock_bridge, non_default_only=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["nonDefaultOnly"] is True

    async def test_non_default_not_set_when_false(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.get_execution_order(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "nonDefaultOnly" not in params

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.get_execution_order(mock_bridge)
        assert _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout") == 15.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        expected = CommandResult(
            success=True,
            data={
                "operation": "get",
                "scripts": [
                    {"scriptPath": "Assets/S.cs", "className": "S", "executionOrder": -100}
                ],
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.get_execution_order(mock_bridge)
        assert result.success is True
        assert len(result.data["scripts"]) == 1


# ---------------------------------------------------------------------------
# set_execution_order
# ---------------------------------------------------------------------------


class TestSetExecutionOrder:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.set_execution_order(mock_bridge, "Assets/Scripts/Init.cs", -100)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "script-execution-order"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.set_execution_order(mock_bridge, "Assets/Scripts/Init.cs", -100)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "set"
        assert params["scriptPath"] == "Assets/Scripts/Init.cs"
        assert params["order"] == -100

    async def test_positive_order(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.set_execution_order(mock_bridge, "Assets/Scripts/Late.cs", 500)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["order"] == 500

    async def test_zero_order(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.set_execution_order(mock_bridge, "Assets/Scripts/Default.cs", 0)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["order"] == 0

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.set_execution_order(mock_bridge, "Assets/Scripts/Init.cs", -100)
        assert _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout") == 15.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        expected = CommandResult(
            success=True,
            data={"operation": "set", "message": "Set execution order"},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.set_execution_order(mock_bridge, "Assets/Scripts/Init.cs", -100)
        assert result.success is True


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

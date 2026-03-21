"""Unit tests for commands/assembly_lock.py — assembly reload lock/unlock."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.core.bridge import CommandResult


def _import_mod():
    from unity_bridge.commands import assembly_lock

    return assembly_lock


# ---------------------------------------------------------------------------
# assembly_lock
# ---------------------------------------------------------------------------


class TestAssemblyLock:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.assembly_lock(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "assembly-reload-lock"

    async def test_sends_lock_operation(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.assembly_lock(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "lock"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.assembly_lock(mock_bridge)
        assert _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout") == 5.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        expected = CommandResult(
            success=True,
            data={"operation": "lock", "isLocked": True, "lockDepth": 1},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.assembly_lock(mock_bridge)
        assert result.success is True
        assert result.data["isLocked"] is True


# ---------------------------------------------------------------------------
# assembly_unlock
# ---------------------------------------------------------------------------


class TestAssemblyUnlock:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.assembly_unlock(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "assembly-reload-lock"

    async def test_sends_unlock_operation(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.assembly_unlock(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "unlock"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.assembly_unlock(mock_bridge)
        assert _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout") == 5.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        expected = CommandResult(
            success=True,
            data={"operation": "unlock", "isLocked": False, "lockDepth": 0},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.assembly_unlock(mock_bridge)
        assert result.success is True
        assert result.data["isLocked"] is False


# ---------------------------------------------------------------------------
# assembly_lock_status
# ---------------------------------------------------------------------------


class TestAssemblyLockStatus:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.assembly_lock_status(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "assembly-reload-lock"

    async def test_sends_status_operation(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.assembly_lock_status(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "status"

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        expected = CommandResult(
            success=True,
            data={"operation": "status", "isLocked": False, "lockDepth": 0},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.assembly_lock_status(mock_bridge)
        assert result.success is True
        assert result.data["lockDepth"] == 0


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

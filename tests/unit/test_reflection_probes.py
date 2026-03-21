"""Unit tests for commands/reflection_probes.py — Reflection probe operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock


from unity_bridge.core.bridge import CommandResult


def _import_probes():
    from unity_bridge.commands import reflection_probes

    return reflection_probes


# ---------------------------------------------------------------------------
# bake
# ---------------------------------------------------------------------------


class TestBake:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_probes()
        await mod.reflection_probe_bake(mock_bridge, "MyProbe")
        assert (
            _extract_command_type(mock_bridge.send_command_with_retry.call_args)
            == "reflection-probe"
        )

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_probes()
        await mod.reflection_probe_bake(mock_bridge, "Env/Probe1")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "bake", "gameObjectPath": "Env/Probe1"}


# ---------------------------------------------------------------------------
# bake-all
# ---------------------------------------------------------------------------


class TestBakeAll:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_probes()
        await mod.reflection_probe_bake_all(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "bake-all"}

    async def test_returns_probe_count(self, mock_bridge: MagicMock) -> None:
        mod = _import_probes()
        expected = CommandResult(
            success=True,
            data={"operation": "bake-all", "probeCount": 3, "success": True},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.reflection_probe_bake_all(mock_bridge)
        assert result.data["probeCount"] == 3


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestList:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_probes()
        await mod.reflection_probe_list(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "list"}


# ---------------------------------------------------------------------------
# get-info
# ---------------------------------------------------------------------------


class TestGetInfo:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_probes()
        await mod.reflection_probe_get_info(mock_bridge, "Env/Probe1")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "get-info", "gameObjectPath": "Env/Probe1"}

    async def test_returns_probe_info(self, mock_bridge: MagicMock) -> None:
        mod = _import_probes()
        expected = CommandResult(
            success=True,
            data={
                "operation": "get-info",
                "mode": "Baked",
                "resolution": 256,
                "intensity": 1.0,
                "success": True,
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.reflection_probe_get_info(mock_bridge, "Probe")
        assert result.data["resolution"] == 256


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

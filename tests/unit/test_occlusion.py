"""Unit tests for commands/occlusion.py — Occlusion culling operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock


from unity_bridge.core.bridge import CommandResult


def _import_occlusion():
    from unity_bridge.commands import occlusion

    return occlusion


# ---------------------------------------------------------------------------
# bake
# ---------------------------------------------------------------------------


class TestBake:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_occlusion()
        await mod.occlusion_bake(mock_bridge)
        assert (
            _extract_command_type(mock_bridge.send_command_with_retry.call_args)
            == "occlusion-culling"
        )

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_occlusion()
        await mod.occlusion_bake(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "bake"}

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_occlusion()
        await mod.occlusion_bake(mock_bridge)
        assert _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout") == 120.0


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------


class TestClear:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_occlusion()
        await mod.occlusion_clear(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "clear"}


# ---------------------------------------------------------------------------
# get-settings
# ---------------------------------------------------------------------------


class TestGetSettings:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_occlusion()
        await mod.occlusion_get_settings(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "get-settings"}

    async def test_returns_settings(self, mock_bridge: MagicMock) -> None:
        mod = _import_occlusion()
        expected = CommandResult(
            success=True,
            data={
                "operation": "get-settings",
                "smallestOccluder": 5.0,
                "smallestHole": 0.25,
                "backfaceThreshold": 100.0,
                "isComputing": False,
                "success": True,
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.occlusion_get_settings(mock_bridge)
        assert result.data["smallestOccluder"] == 5.0
        assert result.data["backfaceThreshold"] == 100.0


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

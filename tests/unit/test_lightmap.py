"""Unit tests for commands/lightmap.py — lightmap bake operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from unity_bridge.core.bridge import CommandResult


def _import_lightmap():
    from unity_bridge.commands import lightmap

    return lightmap


# ---------------------------------------------------------------------------
# bake
# ---------------------------------------------------------------------------


class TestBake:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        lm = _import_lightmap()
        await lm.lightmap_bake(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "lightmap-operation"

    async def test_sends_run_async_true_by_default(self, mock_bridge: MagicMock) -> None:
        lm = _import_lightmap()
        await lm.lightmap_bake(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params == {"operation": "bake", "runAsync": True}

    async def test_sends_run_async_false(self, mock_bridge: MagicMock) -> None:
        lm = _import_lightmap()
        await lm.lightmap_bake(mock_bridge, run_async=False)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params == {"operation": "bake", "runAsync": False}

    async def test_default_timeout_async(self, mock_bridge: MagicMock) -> None:
        lm = _import_lightmap()
        await lm.lightmap_bake(mock_bridge, run_async=True)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 30.0

    async def test_default_timeout_sync(self, mock_bridge: MagicMock) -> None:
        lm = _import_lightmap()
        await lm.lightmap_bake(mock_bridge, run_async=False)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 3600.0

    async def test_custom_timeout(self, mock_bridge: MagicMock) -> None:
        lm = _import_lightmap()
        await lm.lightmap_bake(mock_bridge, timeout=120.0)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 120.0

    async def test_handles_started_false_response(self, mock_bridge: MagicMock) -> None:
        lm = _import_lightmap()
        fail_result = CommandResult(
            success=True,
            data={
                "operation": "bake",
                "started": False,
                "runAsync": True,
                "success": False,
                "message": "Lightmap bake failed to start.",
            },
        )
        mock_bridge.send_command_with_retry.return_value = fail_result
        result = await lm.lightmap_bake(mock_bridge)
        assert result.data["started"] is False

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        lm = _import_lightmap()
        expected = CommandResult(
            success=True,
            data={
                "operation": "bake",
                "started": True,
                "runAsync": True,
                "success": True,
                "message": "Lightmap bake started asynchronously",
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await lm.lightmap_bake(mock_bridge)
        assert result.success is True
        assert result.data["started"] is True


# ---------------------------------------------------------------------------
# cancel
# ---------------------------------------------------------------------------


class TestCancel:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        lm = _import_lightmap()
        await lm.lightmap_cancel(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "lightmap-operation"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        lm = _import_lightmap()
        await lm.lightmap_cancel(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params == {"operation": "cancel"}

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        lm = _import_lightmap()
        await lm.lightmap_cancel(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 30.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        lm = _import_lightmap()
        expected = CommandResult(
            success=True,
            data={"operation": "cancel", "wasRunning": True, "success": True},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await lm.lightmap_cancel(mock_bridge)
        assert result.success is True
        assert result.data["wasRunning"] is True


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------


class TestClear:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        lm = _import_lightmap()
        await lm.lightmap_clear(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "lightmap-operation"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        lm = _import_lightmap()
        await lm.lightmap_clear(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params == {"operation": "clear"}

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        lm = _import_lightmap()
        await lm.lightmap_clear(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 30.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        lm = _import_lightmap()
        expected = CommandResult(
            success=True,
            data={"operation": "clear", "success": True, "message": "Lightmap data cleared"},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await lm.lightmap_clear(mock_bridge)
        assert result.success is True


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


class TestStatus:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        lm = _import_lightmap()
        await lm.lightmap_status(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "lightmap-operation"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        lm = _import_lightmap()
        await lm.lightmap_status(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params == {"operation": "status"}

    async def test_uses_quick_timeout(self, mock_bridge: MagicMock) -> None:
        lm = _import_lightmap()
        await lm.lightmap_status(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 10.0

    async def test_returns_running_status(self, mock_bridge: MagicMock) -> None:
        lm = _import_lightmap()
        expected = CommandResult(
            success=True,
            data={
                "operation": "status",
                "isRunning": True,
                "progress": 0.42,
                "success": True,
                "message": "Lightmap bake in progress (42%)",
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await lm.lightmap_status(mock_bridge)
        assert result.success is True
        assert result.data["isRunning"] is True
        assert result.data["progress"] == pytest.approx(0.42)

    async def test_returns_idle_status(self, mock_bridge: MagicMock) -> None:
        lm = _import_lightmap()
        expected = CommandResult(
            success=True,
            data={
                "operation": "status",
                "isRunning": False,
                "progress": 0.0,
                "success": True,
                "message": "No lightmap bake in progress",
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await lm.lightmap_status(mock_bridge)
        assert result.success is True
        assert result.data["isRunning"] is False


# ---------------------------------------------------------------------------
# settings
# ---------------------------------------------------------------------------


class TestSettings:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        lm = _import_lightmap()
        await lm.lightmap_settings(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "lightmap-operation"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        lm = _import_lightmap()
        await lm.lightmap_settings(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params == {"operation": "settings"}

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        lm = _import_lightmap()
        await lm.lightmap_settings(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 15.0

    async def test_returns_all_settings_fields(self, mock_bridge: MagicMock) -> None:
        lm = _import_lightmap()
        expected = CommandResult(
            success=True,
            data={
                "operation": "settings",
                "lightmapper": "ProgressiveGPU",
                "bakedGI": True,
                "realtimeGI": False,
                "directSamples": 32,
                "indirectSamples": 512,
                "environmentSamples": 256,
                "bounces": 2,
                "lightmapResolution": 40,
                "lightmapPadding": 2,
                "lightmapMaxSize": 1024,
                "compressLightmaps": True,
                "ambientOcclusion": True,
                "aoMaxDistance": 1.0,
                "directionalMode": "Directional",
                "mixedBakeMode": "ShadowMask",
                "success": True,
                "message": "Lightmap settings retrieved",
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await lm.lightmap_settings(mock_bridge)
        assert result.success is True
        assert result.data["lightmapper"] == "ProgressiveGPU"
        assert result.data["bakedGI"] is True
        assert result.data["realtimeGI"] is False
        assert result.data["bounces"] == 2
        assert result.data["lightmapResolution"] == 40
        assert result.data["compressLightmaps"] is True
        assert result.data["ambientOcclusion"] is True


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

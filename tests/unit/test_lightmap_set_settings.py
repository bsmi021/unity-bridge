"""Unit tests for lightmap set-settings extension."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock




def _import_mod():
    from unity_bridge.commands import lightmap

    return lightmap


# ---------------------------------------------------------------------------
# set-settings
# ---------------------------------------------------------------------------


class TestSetSettings:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.lightmap_set_settings(mock_bridge, baked_gi=True)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "lightmap-operation"

    async def test_sends_set_settings_operation(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.lightmap_set_settings(mock_bridge, baked_gi=True)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "set-settings"

    async def test_builds_baked_gi_params(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.lightmap_set_settings(mock_bridge, baked_gi=True)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["bakedGI"] is True
        assert params["setBakedGI"] is True

    async def test_builds_lightmap_size_params(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.lightmap_set_settings(mock_bridge, lightmap_max_size=2048)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["lightmapMaxSize"] == 2048
        assert params["setLightmapMaxSize"] is True

    async def test_builds_bounces_params(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.lightmap_set_settings(mock_bridge, max_bounces=3)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["maxBounces"] == 3
        assert params["setMaxBounces"] is True

    async def test_builds_sample_counts(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.lightmap_set_settings(mock_bridge, direct_samples=64, indirect_samples=1024)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["directSampleCount"] == 64
        assert params["indirectSampleCount"] == 1024

    async def test_omits_unset_params(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.lightmap_set_settings(mock_bridge, baked_gi=True)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert "lightmapMaxSize" not in params
        assert "maxBounces" not in params

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.lightmap_set_settings(mock_bridge, baked_gi=True)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 15.0

    async def test_set_settings_in_valid_actions(self) -> None:
        mod = _import_mod()
        assert "set-settings" in mod.VALID_ACTIONS


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

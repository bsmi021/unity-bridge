"""Unit tests for commands/environment_settings.py — environment settings."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from unity_bridge.core.bridge import CommandResult


def _import_mod():
    from unity_bridge.commands import environment_settings

    return environment_settings


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


class TestEnvironmentGet:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.environment_get(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "environment-settings"

    async def test_sends_get_operation(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.environment_get(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params == {"operation": "get"}

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.environment_get(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 10.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        expected = CommandResult(
            success=True,
            data={
                "operation": "get",
                "fog": True,
                "fogDensity": 0.01,
                "ambientMode": "Skybox",
                "success": True,
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.environment_get(mock_bridge)
        assert result.success is True
        assert result.data["fog"] is True


# ---------------------------------------------------------------------------
# set
# ---------------------------------------------------------------------------


class TestEnvironmentSet:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.environment_set(mock_bridge, fog=True)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "environment-settings"

    async def test_builds_fog_params(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.environment_set(
            mock_bridge, fog=True, fog_density=0.05, fog_color=(0.5, 0.5, 0.5)
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "set"
        assert params["fog"] is True
        assert params["setFog"] is True
        assert params["fogDensity"] == pytest.approx(0.05)
        assert params["fogColorR"] == pytest.approx(0.5)

    async def test_builds_skybox_params(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.environment_set(mock_bridge, skybox_material="Assets/MySkybox.mat")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["skyboxMaterial"] == "Assets/MySkybox.mat"

    async def test_builds_reflection_params(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.environment_set(mock_bridge, reflection_bounces=3, reflection_intensity=0.8)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["reflectionBounces"] == 3
        assert params["setReflectionBounces"] is True
        assert params["reflectionIntensity"] == pytest.approx(0.8)

    async def test_omits_unset_params(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.environment_set(mock_bridge, fog=False)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert "skyboxMaterial" not in params
        assert "fogDensity" not in params

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.environment_set(mock_bridge, fog=True)
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

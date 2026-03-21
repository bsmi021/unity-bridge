"""Unit tests for asset reserialize operation in commands/asset_extended.py."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.core.bridge import CommandResult


def _import_mod():
    from unity_bridge.commands import asset_extended

    return asset_extended


# ---------------------------------------------------------------------------
# reserialize
# ---------------------------------------------------------------------------


class TestReserialize:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.asset_extended_operation(mock_bridge, "reserialize")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "asset-extended-operation"

    async def test_sends_reserialize_operation(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.asset_extended_operation(mock_bridge, "reserialize")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "reserialize"

    async def test_with_specific_paths(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        paths = ["Assets/Prefabs/Player.prefab", "Assets/Materials/Red.mat"]
        await mod.asset_extended_operation(mock_bridge, "reserialize", asset_paths=paths)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["assetPaths"] == paths

    async def test_with_mode_assets(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.asset_extended_operation(mock_bridge, "reserialize", reserialize_mode="assets")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["reserializeMode"] == "assets"

    async def test_with_mode_metadata(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.asset_extended_operation(mock_bridge, "reserialize", reserialize_mode="metadata")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["reserializeMode"] == "metadata"

    async def test_reserialize_all_no_paths(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.asset_extended_operation(mock_bridge, "reserialize")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "assetPaths" not in params

    async def test_returns_success(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        expected = CommandResult(
            success=True,
            data={
                "operation": "reserialize",
                "success": True,
                "message": "Reserialized all project assets",
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.asset_extended_operation(mock_bridge, "reserialize")
        assert result.success is True

    async def test_reserialize_is_valid_operation(self) -> None:
        mod = _import_mod()
        assert "reserialize" in mod.VALID_OPERATIONS

    async def test_reserialize_is_mutating(self) -> None:
        mod = _import_mod()
        assert "reserialize" in mod.MUTATING_OPERATIONS


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

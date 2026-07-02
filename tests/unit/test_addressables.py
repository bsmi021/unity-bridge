"""Unit tests for commands/addressables.py — Addressables operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from unity_bridge.core.bridge import CommandResult


def _import_addressables():
    from unity_bridge.commands import addressables

    return addressables


# ---------------------------------------------------------------------------
# list-groups
# ---------------------------------------------------------------------------


class TestListGroups:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_addressables()
        await mod.addressables_list_groups(mock_bridge)
        assert (
            _extract_command_type(mock_bridge.send_command_with_retry.call_args) == "addressables"
        )

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_addressables()
        await mod.addressables_list_groups(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "list-groups"}

    async def test_returns_groups(self, mock_bridge: MagicMock) -> None:
        mod = _import_addressables()
        expected = CommandResult(
            success=True,
            data={
                "operation": "list-groups",
                "groups": [
                    {"name": "Default Local Group", "entryCount": 5},
                ],
                "success": True,
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.addressables_list_groups(mock_bridge)
        assert len(result.data["groups"]) == 1


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------


class TestBuild:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_addressables()
        await mod.addressables_build(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "build"}

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_addressables()
        await mod.addressables_build(mock_bridge)
        assert _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout") == 120.0


class TestAddressablesBridgeSource:
    def test_csharp_build_uses_result_overload_and_error_mapping(self) -> None:
        source = (
            Path(__file__)
            .resolve()
            .parents[2]
            .joinpath("ClaudeCodeBridge", "AddressablesCommandHandler.cs")
            .read_text(encoding="utf-8")
        )

        assert "AddressablesPlayerBuildResult" in source
        assert 'GetMethod("BuildPlayerContent",' not in source
        assert "GetMethods(" in source
        assert "MakeByRefType()" in source
        assert 'GetProperty("Error")' in source
        assert "Addressables content build failed" in source
        assert "BridgeResponse.Error(command.commandId, command.commandType" in source
        assert 'success = true,\n                message = "Addressable content build started"' not in source


# ---------------------------------------------------------------------------
# clean-cache
# ---------------------------------------------------------------------------


class TestCleanCache:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_addressables()
        await mod.addressables_clean_cache(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "clean-cache"}


# ---------------------------------------------------------------------------
# mark-addressable
# ---------------------------------------------------------------------------


class TestMark:
    async def test_sends_asset_path(self, mock_bridge: MagicMock) -> None:
        mod = _import_addressables()
        await mod.addressables_mark(mock_bridge, "Assets/Prefabs/Enemy.prefab")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "mark-addressable"
        assert params["assetPath"] == "Assets/Prefabs/Enemy.prefab"


# ---------------------------------------------------------------------------
# set-address
# ---------------------------------------------------------------------------


class TestSetAddress:
    async def test_sends_address_key(self, mock_bridge: MagicMock) -> None:
        mod = _import_addressables()
        await mod.addressables_set_address(
            mock_bridge, "Assets/Prefabs/Enemy.prefab", "enemies/basic"
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "set-address"
        assert params["assetPath"] == "Assets/Prefabs/Enemy.prefab"
        assert params["address"] == "enemies/basic"

    async def test_returns_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_addressables()
        expected = CommandResult(
            success=True,
            data={
                "operation": "set-address",
                "address": "enemies/basic",
                "success": True,
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.addressables_set_address(
            mock_bridge, "Assets/Prefabs/Enemy.prefab", "enemies/basic"
        )
        assert result.data["address"] == "enemies/basic"


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

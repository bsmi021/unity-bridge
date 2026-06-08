"""Unit tests for Phase 6 Multiplayer Play Mode surface."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.commands import multiplayer_playmode


def _call_args(mock: MagicMock) -> dict[str, Any]:
    call = mock.send_command_with_retry.call_args
    return call.kwargs if call.kwargs else dict(
        zip(["command_type", "parameters", "timeout"], call.args, strict=False)
    )


class TestMultiplayerPlayMode:
    async def test_availability_dispatches(self, mock_bridge: MagicMock) -> None:
        await multiplayer_playmode.multiplayer_playmode_availability(mock_bridge)

        assert _call_args(mock_bridge)["command_type"] == "multiplayer-playmode"
        assert _call_args(mock_bridge)["parameters"] == {"operation": "availability"}

    async def test_current_player_dispatches(self, mock_bridge: MagicMock) -> None:
        await multiplayer_playmode.multiplayer_playmode_current_player(mock_bridge)

        assert _call_args(mock_bridge)["command_type"] == "multiplayer-playmode"
        assert _call_args(mock_bridge)["parameters"] == {"operation": "current-player"}

    async def test_packages_dispatches(self, mock_bridge: MagicMock) -> None:
        await multiplayer_playmode.multiplayer_playmode_packages(mock_bridge)

        assert _call_args(mock_bridge)["command_type"] == "multiplayer-playmode"
        assert _call_args(mock_bridge)["parameters"] == {"operation": "packages"}


class TestMultiplayerPlayModeSchema:
    def test_schema_includes_expected_operations(self) -> None:
        from unity_bridge.mcp import schemas_multiplayer

        ops = schemas_multiplayer.multiplayer_playmode()["properties"]["operation"]["enum"]

        assert ops == ["availability", "current-player", "packages"]

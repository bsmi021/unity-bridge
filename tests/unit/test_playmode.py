"""Unit tests for commands/playmode.py."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from unity_bridge.commands import playmode

ROOT = Path(__file__).resolve().parents[2]


def _call_args(mock: MagicMock) -> dict[str, Any]:
    call = mock.send_command_with_retry.call_args
    return (
        call.kwargs
        if call.kwargs
        else dict(zip(["command_type", "parameters", "timeout"], call.args, strict=False))
    )


class TestPlaymodeControl:
    async def test_stop_sends_operation_payload_and_timeout(self, mock_bridge: MagicMock) -> None:
        # Arrange
        action = " stop "

        # Act
        await playmode.playmode_control(mock_bridge, action, timeout=12)

        # Assert
        args = _call_args(mock_bridge)
        assert args["command_type"] == "playmode-control"
        assert args["parameters"] == {"operation": "stop"}
        assert args["timeout"] == 12

    async def test_invalid_action_raises(self, mock_bridge: MagicMock) -> None:
        # Arrange
        action = "status"

        # Act / Assert
        with pytest.raises(ValueError, match="Invalid playmode action"):
            await playmode.playmode_control(mock_bridge, action)


class TestPlaymodeCSharpCompatibility:
    def test_legacy_action_alias_is_normalized_before_validation(self) -> None:
        # Arrange
        models = (ROOT / "ClaudeCodeBridge" / "BridgeModels.cs").read_text(encoding="utf-8")
        handler = (ROOT / "ClaudeCodeBridge" / "PlayModeControlCommandHandler.cs").read_text(
            encoding="utf-8"
        )

        # Act
        normalize_index = handler.index("ResolveOperation(parameters)")
        validation_index = handler.index("Operation parameter is required")

        # Assert
        assert "public string action;" in models
        assert normalize_index < validation_index
        assert "parameters.operation = operation;" in handler
        assert "ToLowerInvariant()" in handler

    def test_playmode_transition_persists_across_domain_reload(self) -> None:
        # Arrange
        handler = (ROOT / "ClaudeCodeBridge" / "PlayModeControlCommandHandler.cs").read_text(
            encoding="utf-8"
        )
        store_path = ROOT / "ClaudeCodeBridge" / "PlayModeTransitionStore.cs"
        assert store_path.is_file()
        store = store_path.read_text(encoding="utf-8")
        ledger = (ROOT / "ClaudeCodeBridge" / "BridgeOperationLedger.cs").read_text(
            encoding="utf-8"
        )

        # Act / Assert
        assert "SessionState.SetString(PendingCommandIdKey" in store
        assert "PlayModeTransitionStore.Restore" in handler
        assert "CompletePendingAfterReload" in handler
        assert handler.index("PlayModeTransitionStore.Persist(") < handler.index(
            "EditorApplication.isPlaying = true"
        )
        assert "PlayModeTransitionStore.PendingCommandIdKey" in ledger
        assert "if (EditorApplication.isPlayingOrWillChangePlaymode)" not in store

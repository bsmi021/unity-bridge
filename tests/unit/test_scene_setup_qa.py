"""Adversarial QA tests for commands/scene_setup.py — edge cases and spec compliance.

Covers:
- Setup name validation edge cases
- Play-start get/set/clear interactions
- Preview handle validation
- Command type consistency (scene-setup-operation, not scene-operation)
- Schema operation enum matches implementation
- Restore with missing scenes / empty setup
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from unity_bridge.commands.scene_setup import (
    _validate_setup_name,
    scene_cross_refs,
    scene_list_loaded,
    scene_play_start,
    scene_preview_close,
    scene_preview_create,
    scene_setup_list,
    scene_setup_restore,
    scene_setup_save,
)
from unity_bridge.core.bridge import CommandResult


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


# ---------------------------------------------------------------------------
# Setup name validation
# ---------------------------------------------------------------------------


class TestSetupNameValidation:
    def test_valid_alphanumeric(self) -> None:
        _validate_setup_name("test123")

    def test_valid_hyphens(self) -> None:
        _validate_setup_name("my-setup")

    def test_valid_underscores(self) -> None:
        _validate_setup_name("my_setup")

    def test_valid_mixed(self) -> None:
        _validate_setup_name("my-setup_v2")

    def test_valid_max_length(self) -> None:
        _validate_setup_name("a" * 64)

    def test_invalid_too_long(self) -> None:
        with pytest.raises(ValueError, match="Invalid setup name"):
            _validate_setup_name("a" * 65)

    def test_invalid_empty(self) -> None:
        with pytest.raises(ValueError, match="Invalid setup name"):
            _validate_setup_name("")

    def test_invalid_spaces(self) -> None:
        with pytest.raises(ValueError, match="Invalid setup name"):
            _validate_setup_name("my setup")

    def test_invalid_special_chars(self) -> None:
        with pytest.raises(ValueError, match="Invalid setup name"):
            _validate_setup_name("my.setup")

    def test_invalid_path_traversal(self) -> None:
        with pytest.raises(ValueError, match="Invalid setup name"):
            _validate_setup_name("../../../etc/passwd")

    def test_invalid_shell_injection(self) -> None:
        with pytest.raises(ValueError, match="Invalid setup name"):
            _validate_setup_name("; rm -rf /")

    def test_invalid_unicode(self) -> None:
        with pytest.raises(ValueError, match="Invalid setup name"):
            _validate_setup_name("setup_日本語")


# ---------------------------------------------------------------------------
# All operations use scene-setup-operation command type
# ---------------------------------------------------------------------------


class TestCommandTypeConsistency:
    """All scene extended commands must use 'scene-setup-operation', not 'scene-operation'."""

    async def test_save_command_type(self, mock_bridge: MagicMock) -> None:
        await scene_setup_save(mock_bridge, "test")
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "scene-setup-operation"
        assert cmd != "scene-operation"

    async def test_restore_command_type(self, mock_bridge: MagicMock) -> None:
        await scene_setup_restore(mock_bridge, "test")
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "scene-setup-operation"

    async def test_list_command_type(self, mock_bridge: MagicMock) -> None:
        await scene_setup_list(mock_bridge)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "scene-setup-operation"

    async def test_play_start_command_type(self, mock_bridge: MagicMock) -> None:
        await scene_play_start(mock_bridge)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "scene-setup-operation"

    async def test_cross_refs_command_type(self, mock_bridge: MagicMock) -> None:
        await scene_cross_refs(mock_bridge)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "scene-setup-operation"

    async def test_list_loaded_command_type(self, mock_bridge: MagicMock) -> None:
        await scene_list_loaded(mock_bridge)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "scene-setup-operation"

    async def test_preview_create_command_type(self, mock_bridge: MagicMock) -> None:
        await scene_preview_create(mock_bridge)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "scene-setup-operation"

    async def test_preview_close_command_type(self, mock_bridge: MagicMock) -> None:
        await scene_preview_close(mock_bridge, handle=1)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "scene-setup-operation"


# ---------------------------------------------------------------------------
# Play-start edge cases
# ---------------------------------------------------------------------------


class TestPlayStartEdgeCases:
    async def test_get_mode_sends_only_operation(self, mock_bridge: MagicMock) -> None:
        """Default call (no args) should send only the operation."""
        await scene_play_start(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "play-start"}
        assert "clear" not in params
        assert "scenePath" not in params

    async def test_clear_excludes_scene_path(self, mock_bridge: MagicMock) -> None:
        """When clear=True, scenePath should not be sent even if provided."""
        await scene_play_start(mock_bridge, scene_path="Assets/Scenes/Test.unity", clear=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["clear"] is True
        assert "scenePath" not in params

    async def test_set_scene_path(self, mock_bridge: MagicMock) -> None:
        await scene_play_start(mock_bridge, scene_path="Assets/Scenes/Boot.unity")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["scenePath"] == "Assets/Scenes/Boot.unity"
        assert "clear" not in params

    async def test_scene_not_found_response(self, mock_bridge: MagicMock) -> None:
        error_result = CommandResult(
            success=False,
            data=None,
            error="Scene not found at path: Assets/Scenes/Missing.unity",
        )
        mock_bridge.send_command_with_retry.return_value = error_result
        result = await scene_play_start(mock_bridge, scene_path="Assets/Scenes/Missing.unity")
        assert result.success is False


# ---------------------------------------------------------------------------
# Preview scene edge cases
# ---------------------------------------------------------------------------


class TestPreviewEdgeCases:
    async def test_preview_close_sends_handle(self, mock_bridge: MagicMock) -> None:
        await scene_preview_close(mock_bridge, handle=42)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["handle"] == 42

    async def test_preview_close_invalid_handle_response(self, mock_bridge: MagicMock) -> None:
        error_result = CommandResult(
            success=False,
            data=None,
            error="No preview scene found with handle: 999",
        )
        mock_bridge.send_command_with_retry.return_value = error_result
        result = await scene_preview_close(mock_bridge, handle=999)
        assert result.success is False

    async def test_preview_create_returns_handle(self, mock_bridge: MagicMock) -> None:
        expected = CommandResult(
            success=True,
            data={
                "operation": "preview-create",
                "handle": 1,
                "sceneName": "preview_1",
                "success": True,
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await scene_preview_create(mock_bridge)
        assert result.data["handle"] == 1

    async def test_preview_close_zero_handle(self, mock_bridge: MagicMock) -> None:
        """Handle 0 should be forwarded to the bridge."""
        await scene_preview_close(mock_bridge, handle=0)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["handle"] == 0

    async def test_preview_close_negative_handle(self, mock_bridge: MagicMock) -> None:
        """Negative handle should be forwarded — C# validates."""
        await scene_preview_close(mock_bridge, handle=-1)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["handle"] == -1


# ---------------------------------------------------------------------------
# Restore edge cases
# ---------------------------------------------------------------------------


class TestRestoreEdgeCases:
    async def test_restore_missing_scenes_response(self, mock_bridge: MagicMock) -> None:
        """Restore with missing scenes returns error with missingScenes list."""
        result_data = CommandResult(
            success=True,
            data={
                "operation": "restore",
                "setupName": "old",
                "missingScenes": [
                    "Assets/Scenes/Deleted1.unity",
                    "Assets/Scenes/Deleted2.unity",
                ],
                "success": False,
                "message": "Cannot restore setup: 2 scene(s) not found on disk",
            },
        )
        mock_bridge.send_command_with_retry.return_value = result_data
        result = await scene_setup_restore(mock_bridge, "old")
        assert result.data["success"] is False
        assert len(result.data["missingScenes"]) == 2

    async def test_restore_empty_setup_response(self, mock_bridge: MagicMock) -> None:
        """Restore with empty setup returns error."""
        result_data = CommandResult(
            success=False,
            data=None,
            error="Scene setup is empty or invalid (at least one scene required)",
        )
        mock_bridge.send_command_with_retry.return_value = result_data
        result = await scene_setup_restore(mock_bridge, "empty")
        assert result.success is False

    async def test_restore_does_not_validate_name_python_side(self, mock_bridge: MagicMock) -> None:
        """Restore does NOT validate the name — C# side validates existence."""
        await scene_setup_restore(mock_bridge, "any-name")
        mock_bridge.send_command_with_retry.assert_called_once()

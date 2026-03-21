"""Unit tests for commands/scene_setup.py — extended scene management."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from unity_bridge.core.bridge import CommandResult


def _import_scene_setup():
    from unity_bridge.commands import scene_setup

    return scene_setup


# ---------------------------------------------------------------------------
# setup save
# ---------------------------------------------------------------------------


class TestSetupSave:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        ss = _import_scene_setup()
        await ss.scene_setup_save(mock_bridge, "gameplay-editing")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "scene-setup-operation"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        ss = _import_scene_setup()
        await ss.scene_setup_save(mock_bridge, "my-setup")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params == {"operation": "save", "setupName": "my-setup"}

    async def test_validates_setup_name_alphanumeric(self, mock_bridge: MagicMock) -> None:
        ss = _import_scene_setup()
        with pytest.raises(ValueError, match="Invalid setup name"):
            await ss.scene_setup_save(mock_bridge, "invalid name!")

    async def test_validates_setup_name_max_length(self, mock_bridge: MagicMock) -> None:
        ss = _import_scene_setup()
        with pytest.raises(ValueError, match="Invalid setup name"):
            await ss.scene_setup_save(mock_bridge, "a" * 65)

    async def test_allows_hyphens_and_underscores(self, mock_bridge: MagicMock) -> None:
        ss = _import_scene_setup()
        await ss.scene_setup_save(mock_bridge, "my-setup_v2")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["setupName"] == "my-setup_v2"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        ss = _import_scene_setup()
        await ss.scene_setup_save(mock_bridge, "test")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 30.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        ss = _import_scene_setup()
        expected = CommandResult(
            success=True,
            data={
                "operation": "save",
                "setupName": "gameplay-editing",
                "sceneCount": 3,
                "success": True,
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await ss.scene_setup_save(mock_bridge, "gameplay-editing")
        assert result.success is True
        assert result.data["sceneCount"] == 3


# ---------------------------------------------------------------------------
# setup restore
# ---------------------------------------------------------------------------


class TestSetupRestore:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        ss = _import_scene_setup()
        await ss.scene_setup_restore(mock_bridge, "gameplay-editing")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "scene-setup-operation"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        ss = _import_scene_setup()
        await ss.scene_setup_restore(mock_bridge, "my-setup")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params == {"operation": "restore", "setupName": "my-setup"}

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        ss = _import_scene_setup()
        await ss.scene_setup_restore(mock_bridge, "test")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 30.0

    async def test_handles_missing_scenes_error(self, mock_bridge: MagicMock) -> None:
        ss = _import_scene_setup()
        expected = CommandResult(
            success=True,
            data={
                "operation": "restore",
                "setupName": "old-setup",
                "success": False,
                "missingScenes": ["Assets/Scenes/DeletedScene.unity"],
                "message": "Cannot restore setup: 1 scene(s) not found on disk",
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await ss.scene_setup_restore(mock_bridge, "old-setup")
        assert result.data["success"] is False
        assert len(result.data["missingScenes"]) == 1


# ---------------------------------------------------------------------------
# setup list
# ---------------------------------------------------------------------------


class TestSetupList:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        ss = _import_scene_setup()
        await ss.scene_setup_list(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "scene-setup-operation"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        ss = _import_scene_setup()
        await ss.scene_setup_list(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params == {"operation": "list"}

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        ss = _import_scene_setup()
        expected = CommandResult(
            success=True,
            data={"operation": "list", "setupCount": 2, "success": True},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await ss.scene_setup_list(mock_bridge)
        assert result.success is True
        assert result.data["setupCount"] == 2


# ---------------------------------------------------------------------------
# play-start
# ---------------------------------------------------------------------------


class TestPlayStart:
    async def test_get_sends_no_extra_params(self, mock_bridge: MagicMock) -> None:
        ss = _import_scene_setup()
        await ss.scene_play_start(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params == {"operation": "play-start"}

    async def test_set_sends_scene_path(self, mock_bridge: MagicMock) -> None:
        ss = _import_scene_setup()
        await ss.scene_play_start(mock_bridge, scene_path="Assets/Scenes/Main.unity")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params == {
            "operation": "play-start",
            "scenePath": "Assets/Scenes/Main.unity",
        }

    async def test_clear_sends_clear_true(self, mock_bridge: MagicMock) -> None:
        ss = _import_scene_setup()
        await ss.scene_play_start(mock_bridge, clear=True)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params == {"operation": "play-start", "clear": True}

    async def test_clear_takes_precedence_over_set(self, mock_bridge: MagicMock) -> None:
        ss = _import_scene_setup()
        await ss.scene_play_start(mock_bridge, scene_path="Assets/Scenes/X.unity", clear=True)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        # clear=True should win, no scenePath
        assert "scenePath" not in params
        assert params["clear"] is True

    async def test_returns_current_start_scene(self, mock_bridge: MagicMock) -> None:
        ss = _import_scene_setup()
        expected = CommandResult(
            success=True,
            data={
                "operation": "play-start",
                "playModeStartScene": "Assets/Scenes/Bootstrap.unity",
                "isSet": True,
                "success": True,
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await ss.scene_play_start(mock_bridge)
        assert result.data["playModeStartScene"] == "Assets/Scenes/Bootstrap.unity"


# ---------------------------------------------------------------------------
# cross-refs
# ---------------------------------------------------------------------------


class TestCrossRefs:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        ss = _import_scene_setup()
        await ss.scene_cross_refs(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "scene-setup-operation"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        ss = _import_scene_setup()
        await ss.scene_cross_refs(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params == {"operation": "cross-refs"}


# ---------------------------------------------------------------------------
# list-loaded
# ---------------------------------------------------------------------------


class TestListLoaded:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        ss = _import_scene_setup()
        await ss.scene_list_loaded(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "scene-setup-operation"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        ss = _import_scene_setup()
        await ss.scene_list_loaded(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params == {"operation": "list-loaded"}


# ---------------------------------------------------------------------------
# preview-create
# ---------------------------------------------------------------------------


class TestPreviewCreate:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        ss = _import_scene_setup()
        await ss.scene_preview_create(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "scene-setup-operation"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        ss = _import_scene_setup()
        await ss.scene_preview_create(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params == {"operation": "preview-create"}

    async def test_returns_handle(self, mock_bridge: MagicMock) -> None:
        ss = _import_scene_setup()
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
        result = await ss.scene_preview_create(mock_bridge)
        assert result.data["handle"] == 1


# ---------------------------------------------------------------------------
# preview-close
# ---------------------------------------------------------------------------


class TestPreviewClose:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        ss = _import_scene_setup()
        await ss.scene_preview_close(mock_bridge, handle=1)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "scene-setup-operation"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        ss = _import_scene_setup()
        await ss.scene_preview_close(mock_bridge, handle=3)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params == {"operation": "preview-close", "handle": 3}

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        ss = _import_scene_setup()
        await ss.scene_preview_close(mock_bridge, handle=1)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 30.0


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

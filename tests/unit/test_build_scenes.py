"""Unit tests for commands/build_scenes.py — Build Settings scene management."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.core.bridge import CommandResult


def _import_build_scenes():
    from unity_bridge.commands import build_scenes

    return build_scenes


# ---------------------------------------------------------------------------
# scenes_list
# ---------------------------------------------------------------------------


class TestScenesList:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_build_scenes()
        await mod.scenes_list(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "build-scenes"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_build_scenes()
        await mod.scenes_list(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "list"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_build_scenes()
        await mod.scenes_list(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 10.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_build_scenes()
        expected = CommandResult(
            success=True,
            data={"count": 2, "scenes": []},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.scenes_list(mock_bridge)
        assert result.success is True
        assert result.data["count"] == 2


# ---------------------------------------------------------------------------
# scenes_add
# ---------------------------------------------------------------------------


class TestScenesAdd:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_build_scenes()
        await mod.scenes_add(mock_bridge, scene_path="Assets/Scenes/Main.unity")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "build-scenes"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_build_scenes()
        await mod.scenes_add(mock_bridge, scene_path="Assets/Scenes/Main.unity")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "add"
        assert params["scenePath"] == "Assets/Scenes/Main.unity"

    async def test_index_parameter(self, mock_bridge: MagicMock) -> None:
        mod = _import_build_scenes()
        await mod.scenes_add(mock_bridge, scene_path="Assets/Scenes/Main.unity", index=0)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["index"] == 0

    async def test_no_index_when_default(self, mock_bridge: MagicMock) -> None:
        mod = _import_build_scenes()
        await mod.scenes_add(mock_bridge, scene_path="Assets/Scenes/Main.unity")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert "index" not in params

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_build_scenes()
        await mod.scenes_add(mock_bridge, scene_path="Assets/Scenes/Main.unity")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 15.0


# ---------------------------------------------------------------------------
# scenes_remove
# ---------------------------------------------------------------------------


class TestScenesRemove:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_build_scenes()
        await mod.scenes_remove(mock_bridge, scene_path="Assets/Scenes/Old.unity")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "build-scenes"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_build_scenes()
        await mod.scenes_remove(mock_bridge, scene_path="Assets/Scenes/Old.unity")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "remove"
        assert params["scenePath"] == "Assets/Scenes/Old.unity"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_build_scenes()
        await mod.scenes_remove(mock_bridge, scene_path="Assets/Scenes/Old.unity")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 15.0


# ---------------------------------------------------------------------------
# scenes_enable / scenes_disable
# ---------------------------------------------------------------------------


class TestScenesEnable:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_build_scenes()
        await mod.scenes_enable(mock_bridge, scene_path="Assets/Scenes/Level1.unity")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "enable"
        assert params["scenePath"] == "Assets/Scenes/Level1.unity"


class TestScenesDisable:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_build_scenes()
        await mod.scenes_disable(mock_bridge, scene_path="Assets/Scenes/Level1.unity")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "disable"
        assert params["scenePath"] == "Assets/Scenes/Level1.unity"


# ---------------------------------------------------------------------------
# duplicate (in hierarchy)
# ---------------------------------------------------------------------------


class TestDuplicateGameObject:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands import hierarchy

        await hierarchy.duplicate_gameobject(mock_bridge, object_path="Player")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "gameobject-utility"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands import hierarchy

        await hierarchy.duplicate_gameobject(mock_bridge, object_path="Player")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "duplicate"
        assert params["gameObjectPath"] == "Player"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands import hierarchy

        await hierarchy.duplicate_gameobject(mock_bridge, object_path="Player")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 15.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands import hierarchy

        expected = CommandResult(
            success=True,
            data={
                "operation": "duplicate",
                "path": "Player",
                "duplicatePath": "Player (1)",
                "duplicateName": "Player (1)",
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await hierarchy.duplicate_gameobject(mock_bridge, object_path="Player")
        assert result.success is True
        assert result.data["duplicatePath"] == "Player (1)"


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

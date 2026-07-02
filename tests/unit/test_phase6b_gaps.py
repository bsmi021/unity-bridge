"""Unit tests for Phase 6b: Scene/Material/Component/Inspector gaps."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock


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
# Material keyword operations
# ---------------------------------------------------------------------------


class TestMaterialEnableKeyword:
    async def test_sends_correct_command(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.material import material_enable_keyword

        await material_enable_keyword(mock_bridge, "Assets/M.mat", "_EMISSION")
        call = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call) == "material-operation"

    async def test_sends_correct_params(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.material import material_enable_keyword

        await material_enable_keyword(mock_bridge, "Assets/M.mat", "_EMISSION")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "enable-keyword"
        assert params["materialPath"] == "Assets/M.mat"
        assert params["keyword"] == "_EMISSION"


class TestMaterialDisableKeyword:
    async def test_sends_correct_params(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.material import material_disable_keyword

        await material_disable_keyword(mock_bridge, "Assets/M.mat", "_EMISSION")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "disable-keyword"
        assert params["keyword"] == "_EMISSION"


class TestMaterialGetKeywords:
    async def test_sends_correct_command(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.material import material_get_keywords

        await material_get_keywords(mock_bridge, "Assets/M.mat")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "get-keywords"
        assert params["materialPath"] == "Assets/M.mat"


class TestMaterialSetRenderQueue:
    async def test_sends_correct_params(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.material import material_set_render_queue

        await material_set_render_queue(mock_bridge, "Assets/M.mat", 3000)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "set-render-queue"
        assert params["renderQueue"] == 3000


class TestMaterialCopyProperties:
    async def test_sends_correct_params(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.material import material_copy_properties

        await material_copy_properties(mock_bridge, "Assets/Target.mat", "Assets/Source.mat")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "copy-properties"
        assert params["materialPath"] == "Assets/Target.mat"
        assert params["sourceMaterialPath"] == "Assets/Source.mat"


# ---------------------------------------------------------------------------
# Component copy/paste
# ---------------------------------------------------------------------------


class TestComponentCopy:
    async def test_sends_correct_command(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.component_ext import component_copy

        await component_copy(mock_bridge, "Player", "BoxCollider")
        call = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call) == "component-copy"

    async def test_sends_correct_params(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.component_ext import component_copy

        await component_copy(mock_bridge, "Player", "BoxCollider")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "copy"
        assert params["gameObjectPath"] == "Player"
        assert params["componentType"] == "BoxCollider"


class TestComponentPaste:
    async def test_sends_correct_params(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.component_ext import component_paste

        await component_paste(mock_bridge, "Enemy", "BoxCollider")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "paste"
        assert params["gameObjectPath"] == "Enemy"

    async def test_with_data_json(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.component_ext import component_paste

        await component_paste(mock_bridge, "Enemy", "BoxCollider", data_json='{"size":2}')
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["dataJson"] == '{"size":2}'

    async def test_without_data_json(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.component_ext import component_paste

        await component_paste(mock_bridge, "Enemy", "BoxCollider")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "dataJson" not in params


# ---------------------------------------------------------------------------
# Component reset
# ---------------------------------------------------------------------------


class TestComponentReset:
    async def test_sends_correct_command(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.component_ext import component_reset

        await component_reset(mock_bridge, "Player", "Rigidbody")
        call = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call) == "component-reset"

    async def test_sends_correct_params(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.component_ext import component_reset

        await component_reset(mock_bridge, "Player", "Rigidbody")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["gameObjectPath"] == "Player"
        assert params["componentType"] == "Rigidbody"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.component_ext import component_reset

        await component_reset(mock_bridge, "P", "C")
        call = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call, "timeout") == 15.0


# ---------------------------------------------------------------------------
# Scene move-object
# ---------------------------------------------------------------------------


class TestSceneMoveObject:
    async def test_sends_correct_command(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.scene import scene_move_object

        await scene_move_object(mock_bridge, "Player", "Assets/Scenes/Other.unity")
        call = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call) == "scene-operation"

    async def test_sends_correct_params(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.scene import scene_move_object

        await scene_move_object(mock_bridge, "Player", "Assets/Scenes/Other.unity")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "move-object"
        assert params["gameObjectPath"] == "Player"
        assert params["scenePath"] == "Assets/Scenes/Other.unity"


# ---------------------------------------------------------------------------
# Scene View
# ---------------------------------------------------------------------------


class TestSceneViewGet:
    async def test_sends_correct_command(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.scene_view import scene_view_get

        await scene_view_get(mock_bridge)
        call = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call) == "scene-view"

    async def test_sends_get_camera_op(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.scene_view import scene_view_get

        await scene_view_get(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "get-camera"


class TestSceneViewSet:
    async def test_sends_pivot(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.scene_view import scene_view_set

        await scene_view_set(mock_bridge, pivot=(1.0, 2.0, 3.0))
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "set-camera"
        assert params["pivot"]["x"] == 1.0
        assert params["pivot"]["y"] == 2.0
        assert params["pivot"]["z"] == 3.0

    async def test_sends_rotation_and_size(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.scene_view import scene_view_set

        await scene_view_set(mock_bridge, rotation=(45.0, 90.0, 0.0), size=10.0)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["rotation"]["x"] == 45.0
        assert params["size"] == 10.0

    async def test_orthographic(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.scene_view import scene_view_set

        await scene_view_set(mock_bridge, orthographic=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["orthographic"] is True

    async def test_perspective(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.scene_view import scene_view_set

        await scene_view_set(mock_bridge, orthographic=False)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["setPerspective"] is True


class TestSceneViewToggle2D:
    async def test_enable(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.scene_view import scene_view_toggle_2d

        await scene_view_toggle_2d(mock_bridge, enable=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "toggle-2d"
        assert params["enable2D"] is True

    async def test_disable(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.scene_view import scene_view_toggle_2d

        await scene_view_toggle_2d(mock_bridge, enable=False)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["enable2D"] is False


class TestSceneViewSetDrawMode:
    async def test_sends_draw_mode(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.scene_view import scene_view_set_draw_mode

        await scene_view_set_draw_mode(mock_bridge, "Wireframe")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "set-draw-mode"
        assert params["drawMode"] == "Wireframe"


# ---------------------------------------------------------------------------
# Game View
# ---------------------------------------------------------------------------


class TestGameViewGet:
    async def test_sends_correct_command(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.game_view import game_view_get

        await game_view_get(mock_bridge)
        call = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call) == "game-view"

    async def test_sends_get_op(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.game_view import game_view_get

        await game_view_get(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "get"


class TestGameViewSetResolution:
    async def test_sends_correct_params(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.game_view import game_view_set_resolution

        await game_view_set_resolution(mock_bridge, 1920, 1080)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "set-resolution"
        assert params["width"] == 1920
        assert params["height"] == 1080


class TestGameViewSetScale:
    async def test_sends_correct_params(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.game_view import game_view_set_scale

        await game_view_set_scale(mock_bridge, 2.0)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "set-scale"
        assert params["scale"] == 2.0


# ---------------------------------------------------------------------------
# Profiler Control
# ---------------------------------------------------------------------------


class TestProfilerStart:
    async def test_sends_correct_command(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.profiler import profiler_start

        await profiler_start(mock_bridge)
        call = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call) == "profiler-control"

    async def test_basic_start(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.profiler import profiler_start

        await profiler_start(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "start"
        assert "logFile" not in params

    async def test_start_with_log_file(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.profiler import profiler_start

        await profiler_start(mock_bridge, log_file="/tmp/profiler.raw")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["logFile"] == "/tmp/profiler.raw"


class TestProfilerStop:
    async def test_sends_stop(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.profiler import profiler_stop

        await profiler_stop(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "stop"


class TestProfilerSave:
    async def test_sends_save(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.profiler import profiler_save

        await profiler_save(mock_bridge, "/tmp/profiler.raw")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "save"
        assert params["logFile"] == "/tmp/profiler.raw"


class TestProfilerMemory:
    async def test_sends_memory(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.profiler import profiler_memory

        await profiler_memory(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "memory"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.profiler import profiler_memory

        await profiler_memory(mock_bridge)
        call = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call, "timeout") == 10.0


class TestProfilerSetAreas:
    async def test_sends_set_areas(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.profiler import profiler_set_areas

        await profiler_set_areas(
            mock_bridge,
            areas=["Physics", "Audio"],
            enabled=False,
            allocation_callstacks=True,
        )

        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "set-areas"
        assert params["areas"] == "Physics,Audio"
        assert params["enabled"] is False
        assert params["allocationCallstacks"] is True


# ---------------------------------------------------------------------------
# Material legacy action validation
# ---------------------------------------------------------------------------


class TestMaterialOperationValidation:
    async def test_invalid_action_raises(self, mock_bridge: MagicMock) -> None:
        import pytest
        from unity_bridge.commands.material import material_operation

        with pytest.raises(ValueError, match="Invalid material action"):
            await material_operation(mock_bridge, "invalid", "Assets/M.mat")

    async def test_valid_actions(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.material import material_operation

        for action in ("modify", "create", "duplicate"):
            await material_operation(mock_bridge, action, "Assets/M.mat")
            params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
            assert params["operation"] == action

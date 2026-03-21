"""Unit tests for commands/hierarchy_ext.py — Phase 5 quick wins."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock


def _import_ext():
    from unity_bridge.commands import hierarchy_ext

    return hierarchy_ext


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
# create_primitive
# ---------------------------------------------------------------------------


class TestCreatePrimitive:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_ext()
        await mod.create_primitive(mock_bridge, "cube")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "gameobject-operation"

    async def test_sends_correct_params(self, mock_bridge: MagicMock) -> None:
        mod = _import_ext()
        await mod.create_primitive(mock_bridge, "sphere", name="MySphere")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "create-primitive"
        assert params["primitiveType"] == "sphere"
        assert params["gameObjectName"] == "MySphere"

    async def test_optional_parent(self, mock_bridge: MagicMock) -> None:
        mod = _import_ext()
        await mod.create_primitive(mock_bridge, "cube", parent="Environment")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["parentPath"] == "Environment"

    async def test_no_parent_no_name(self, mock_bridge: MagicMock) -> None:
        mod = _import_ext()
        await mod.create_primitive(mock_bridge, "plane")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "parentPath" not in params
        assert "gameObjectName" not in params

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_ext()
        await mod.create_primitive(mock_bridge, "cube")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 15.0


# ---------------------------------------------------------------------------
# set_active
# ---------------------------------------------------------------------------


class TestSetActive:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_ext()
        await mod.set_active(mock_bridge, "Player", active=False)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "gameobject-operation"

    async def test_sends_correct_params(self, mock_bridge: MagicMock) -> None:
        mod = _import_ext()
        await mod.set_active(mock_bridge, "Player", active=False)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "set-active"
        assert params["gameObjectPath"] == "Player"
        assert params["active"] is False

    async def test_default_active_true(self, mock_bridge: MagicMock) -> None:
        mod = _import_ext()
        await mod.set_active(mock_bridge, "Player")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["active"] is True


# ---------------------------------------------------------------------------
# remove_component
# ---------------------------------------------------------------------------


class TestRemoveComponent:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_ext()
        await mod.remove_component(mock_bridge, "Player", "Rigidbody")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "remove-component"

    async def test_sends_correct_params(self, mock_bridge: MagicMock) -> None:
        mod = _import_ext()
        await mod.remove_component(mock_bridge, "Player", "BoxCollider")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["gameObjectPath"] == "Player"
        assert params["componentType"] == "BoxCollider"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_ext()
        await mod.remove_component(mock_bridge, "P", "C")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 15.0


# ---------------------------------------------------------------------------
# component_toggle
# ---------------------------------------------------------------------------


class TestComponentToggle:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_ext()
        await mod.component_toggle(mock_bridge, "Player", "MeshRenderer", False)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "component-toggle"

    async def test_enable(self, mock_bridge: MagicMock) -> None:
        mod = _import_ext()
        await mod.component_toggle(mock_bridge, "Player", "Collider", True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["enabled"] is True

    async def test_disable(self, mock_bridge: MagicMock) -> None:
        mod = _import_ext()
        await mod.component_toggle(mock_bridge, "Player", "Collider", False)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["enabled"] is False

    async def test_sends_correct_params(self, mock_bridge: MagicMock) -> None:
        mod = _import_ext()
        await mod.component_toggle(mock_bridge, "P/C", "Light", True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["gameObjectPath"] == "P/C"
        assert params["componentType"] == "Light"


# ---------------------------------------------------------------------------
# scene_load_additive
# ---------------------------------------------------------------------------


class TestSceneLoadAdditive:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_ext()
        await mod.scene_load_additive(mock_bridge, "Assets/Scenes/Test.unity")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "scene-operation"

    async def test_sends_additive_mode(self, mock_bridge: MagicMock) -> None:
        mod = _import_ext()
        await mod.scene_load_additive(mock_bridge, "Assets/Scenes/Test.unity")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["mode"] == "additive"
        assert params["operation"] == "load"

    async def test_save_current(self, mock_bridge: MagicMock) -> None:
        mod = _import_ext()
        await mod.scene_load_additive(mock_bridge, "Assets/Scenes/Test.unity", save_current=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["saveCurrentScene"] is True


# ---------------------------------------------------------------------------
# scene_unload
# ---------------------------------------------------------------------------


class TestSceneUnload:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_ext()
        await mod.scene_unload(mock_bridge, "Assets/Scenes/Test.unity")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "scene-operation"

    async def test_unload_params(self, mock_bridge: MagicMock) -> None:
        mod = _import_ext()
        await mod.scene_unload(mock_bridge, "Assets/Scenes/Test.unity")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "unload"
        assert params["removeScene"] is True

    async def test_unload_keep(self, mock_bridge: MagicMock) -> None:
        mod = _import_ext()
        await mod.scene_unload(mock_bridge, "Assets/Scenes/Test.unity", remove=False)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["removeScene"] is False


# ---------------------------------------------------------------------------
# scene_set_active
# ---------------------------------------------------------------------------


class TestSceneSetActive:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_ext()
        await mod.scene_set_active(mock_bridge, "Assets/Scenes/Test.unity")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "scene-operation"

    async def test_set_active_params(self, mock_bridge: MagicMock) -> None:
        mod = _import_ext()
        await mod.scene_set_active(mock_bridge, "Assets/Scenes/Test.unity")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "set-active"
        assert params["scenePath"] == "Assets/Scenes/Test.unity"


# ---------------------------------------------------------------------------
# console_log
# ---------------------------------------------------------------------------


class TestConsoleLog:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_ext()
        await mod.console_log(mock_bridge, "hello")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "console-log"

    async def test_default_log_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_ext()
        await mod.console_log(mock_bridge, "hello")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["logType"] == "log"
        assert params["message"] == "hello"

    async def test_warning_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_ext()
        await mod.console_log(mock_bridge, "oops", log_type="warning")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["logType"] == "warning"

    async def test_error_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_ext()
        await mod.console_log(mock_bridge, "fail", log_type="error")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["logType"] == "error"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_ext()
        await mod.console_log(mock_bridge, "x")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 5.0


# ---------------------------------------------------------------------------
# scene_load with --additive flag
# ---------------------------------------------------------------------------


class TestSceneLoadAdditiveFlag:
    async def test_scene_load_additive_flag(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.scene import scene_load

        await scene_load(mock_bridge, "Assets/Scenes/Test.unity", additive=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["mode"] == "additive"

    async def test_scene_load_default_not_additive(self, mock_bridge: MagicMock) -> None:
        from unity_bridge.commands.scene import scene_load

        await scene_load(mock_bridge, "Assets/Scenes/Test.unity")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "mode" not in params

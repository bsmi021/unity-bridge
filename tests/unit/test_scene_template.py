"""Unit tests for commands/scene_template.py — scene template operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock


def _import_scene_template():
    from unity_bridge.commands import scene_template

    return scene_template


class TestSceneTemplateList:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_scene_template()
        await mod.scene_template_list(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "scene-template"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_scene_template()
        await mod.scene_template_list(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "list"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_scene_template()
        await mod.scene_template_list(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 10.0


class TestSceneTemplateCreate:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_scene_template()
        await mod.scene_template_create(
            mock_bridge, "Assets/Scenes/Main.unity", "Assets/Templates/Main.scenetemplate"
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "create-from-scene"
        assert params["scenePath"] == "Assets/Scenes/Main.unity"
        assert params["outputPath"] == "Assets/Templates/Main.scenetemplate"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_scene_template()
        await mod.scene_template_create(mock_bridge, "a.unity", "b.scenetemplate")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 30.0


class TestSceneTemplateInstantiate:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_scene_template()
        await mod.scene_template_instantiate(mock_bridge, "Assets/T/Main.scenetemplate")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "instantiate"
        assert params["templatePath"] == "Assets/T/Main.scenetemplate"

    async def test_optional_output_path(self, mock_bridge: MagicMock) -> None:
        mod = _import_scene_template()
        await mod.scene_template_instantiate(
            mock_bridge, "Assets/T/Main.scenetemplate", "Assets/Scenes/New.unity"
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["outputPath"] == "Assets/Scenes/New.unity"

    async def test_no_output_path_excludes_key(self, mock_bridge: MagicMock) -> None:
        mod = _import_scene_template()
        await mod.scene_template_instantiate(mock_bridge, "Assets/T/Main.scenetemplate")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert "outputPath" not in params


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

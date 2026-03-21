"""Unit tests for commands/find_references.py — find asset references in scene."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.core.bridge import CommandResult


def _import_mod():
    from unity_bridge.commands import find_references

    return find_references


# ---------------------------------------------------------------------------
# find_references_in_scene
# ---------------------------------------------------------------------------


class TestFindReferencesInScene:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.find_references_in_scene(mock_bridge, "Assets/Materials/Red.mat")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "find-references"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.find_references_in_scene(mock_bridge, "Assets/Materials/Red.mat")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "find-in-scene"
        assert params["assetPath"] == "Assets/Materials/Red.mat"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.find_references_in_scene(mock_bridge, "Assets/Materials/Red.mat")
        assert _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout") == 30.0

    async def test_custom_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.find_references_in_scene(mock_bridge, "Assets/Materials/Red.mat", timeout=60.0)
        assert _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout") == 60.0

    async def test_returns_references(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        expected = CommandResult(
            success=True,
            data={
                "operation": "find-in-scene",
                "assetPath": "Assets/Materials/Red.mat",
                "assetType": "Material",
                "totalReferences": 2,
                "references": [
                    {
                        "gameObjectPath": "Cube",
                        "sceneName": "SampleScene",
                        "componentType": "MeshRenderer",
                        "propertyPath": "m_Materials.Array.data[0]",
                    },
                    {
                        "gameObjectPath": "Floor",
                        "sceneName": "SampleScene",
                        "componentType": "MeshRenderer",
                        "propertyPath": "m_Materials.Array.data[0]",
                    },
                ],
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.find_references_in_scene(mock_bridge, "Assets/Materials/Red.mat")
        assert result.success is True
        assert result.data["totalReferences"] == 2
        assert len(result.data["references"]) == 2

    async def test_returns_empty_when_no_references(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        expected = CommandResult(
            success=True,
            data={
                "operation": "find-in-scene",
                "assetPath": "Assets/Unused.mat",
                "totalReferences": 0,
                "references": [],
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.find_references_in_scene(mock_bridge, "Assets/Unused.mat")
        assert result.success is True
        assert result.data["totalReferences"] == 0


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

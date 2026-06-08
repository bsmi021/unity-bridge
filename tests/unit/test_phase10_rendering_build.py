"""Unit tests for Phase 3 rendering/build pipeline surfaces."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.commands import build_profile, graphics_state, render_pipeline


def _call_args(mock: MagicMock) -> dict[str, Any]:
    call = mock.send_command_with_retry.call_args
    return call.kwargs if call.kwargs else dict(
        zip(["command_type", "parameters", "timeout"], call.args, strict=False)
    )


class TestRenderPipeline:
    async def test_list_assets_dispatches(self, mock_bridge: MagicMock) -> None:
        await render_pipeline.render_pipeline_list_assets(mock_bridge)

        assert _call_args(mock_bridge)["command_type"] == "render-pipeline"
        assert _call_args(mock_bridge)["parameters"] == {"operation": "list-assets"}

    async def test_set_quality_dispatches(self, mock_bridge: MagicMock) -> None:
        await render_pipeline.render_pipeline_set_quality(
            mock_bridge,
            asset_path="Assets/Settings/URP.asset",
            quality_level="High",
        )

        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "set-quality",
            "assetPath": "Assets/Settings/URP.asset",
            "qualityLevel": "High",
        }


class TestGraphicsState:
    async def test_create_dispatches(self, mock_bridge: MagicMock) -> None:
        await graphics_state.graphics_state_create(mock_bridge, "Temp/pso.graphicsstate")

        assert _call_args(mock_bridge)["command_type"] == "graphics-state"
        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "create",
            "outputPath": "Temp/pso.graphicsstate",
        }

    async def test_warmup_progressive_dispatches(self, mock_bridge: MagicMock) -> None:
        await graphics_state.graphics_state_warmup(
            mock_bridge,
            "Temp/pso.graphicsstate",
            progressive_batch_size=8,
        )

        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "warmup",
            "assetPath": "Temp/pso.graphicsstate",
            "progressiveBatchSize": 8,
        }


class TestBuildProfileDeepening:
    async def test_set_scenes_dispatches(self, mock_bridge: MagicMock) -> None:
        await build_profile.build_profile_operation(
            mock_bridge,
            "set-scenes",
            profile_path="Assets/Build/Windows.asset",
            scenes=["Assets/Scenes/Main.unity"],
            disabled_scenes=["Assets/Scenes/Debug.unity"],
        )

        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "set-scenes",
            "profilePath": "Assets/Build/Windows.asset",
            "scenes": ["Assets/Scenes/Main.unity"],
            "disabledScenes": ["Assets/Scenes/Debug.unity"],
        }

    async def test_build_dispatches(self, mock_bridge: MagicMock) -> None:
        await build_profile.build_profile_operation(
            mock_bridge,
            "build",
            profile_path="Assets/Build/Windows.asset",
            output_path="Builds/Windows/Game.exe",
            development=True,
        )

        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "build",
            "profilePath": "Assets/Build/Windows.asset",
            "outputPath": "Builds/Windows/Game.exe",
            "development": True,
        }


class TestRenderingBuildRegistration:
    def test_tool_map_entries(self) -> None:
        from unity_bridge.mcp.tools import TOOL_COMMAND_MAP

        assert TOOL_COMMAND_MAP["unity_render_pipeline"] == "render-pipeline"
        assert TOOL_COMMAND_MAP["unity_graphics_state"] == "graphics-state"
        assert TOOL_COMMAND_MAP["unity_build_profile"] == "build-profile-operation"

    def test_timeout_defaults(self) -> None:
        from unity_bridge.core.protocol import TIMEOUT_DEFAULTS

        assert TIMEOUT_DEFAULTS["render-pipeline"] == 15
        assert TIMEOUT_DEFAULTS["graphics-state"] == 300
        assert TIMEOUT_DEFAULTS["build-profile-operation"] == 300

    def test_schemas_include_new_operations(self) -> None:
        from unity_bridge.mcp import schemas_ext, schemas_rendering

        build_ops = schemas_ext.build_profile()["properties"]["operation"]["enum"]
        render_ops = schemas_rendering.render_pipeline()["properties"]["operation"]["enum"]
        pso_ops = schemas_rendering.graphics_state()["properties"]["operation"]["enum"]
        assert "set-scenes" in build_ops
        assert "set-default" in render_ops
        assert "warmup" in pso_ops

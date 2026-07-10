"""Unit tests for editor screenshot capture."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock


ROOT = Path(__file__).resolve().parents[2]


class TestScreenshotPayload:
    async def test_capture_screenshot_can_request_inline_base64(
        self, mock_bridge: MagicMock
    ) -> None:
        from unity_bridge.commands.editor import capture_screenshot

        await capture_screenshot(
            mock_bridge,
            "Screenshots/test.png",
            return_base64=True,
            multi_angle=True,
        )

        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["outputPath"] == "Screenshots/test.png"
        assert params["returnBase64"] is True
        assert params["multiAngle"] is True

    def test_csharp_screenshot_supports_inline_and_multi_angle(self) -> None:
        handler_source = ROOT.joinpath(
            "ClaudeCodeBridge", "CaptureScreenshotCommandHandler.cs"
        ).read_text(encoding="utf-8")
        model_source = ROOT.joinpath("ClaudeCodeBridge", "BridgeModels.cs").read_text(
            encoding="utf-8"
        )

        assert "returnBase64" in model_source
        assert "base64Png" in model_source
        assert "multiAngle" in model_source
        assert "CaptureMultiAngle" in handler_source
        assert "Convert.ToBase64String" in handler_source

    def test_multi_angle_capture_restores_scene_view_state_in_finally(self) -> None:
        # Arrange
        handler_source = ROOT.joinpath(
            "ClaudeCodeBridge", "CaptureScreenshotCommandHandler.cs"
        ).read_text(encoding="utf-8")

        # Act / Assert
        assert "CaptureSceneViewState" in handler_source
        assert "RestoreSceneViewState" in handler_source
        assert "finally" in handler_source
        assert "sceneView.pivot" in handler_source
        assert "sceneView.rotation" in handler_source
        assert "sceneView.size" in handler_source
        assert "sceneView.orthographic" in handler_source
        assert (
            "sceneView.LookAt(sceneView.pivot, rotation, sceneView.size, "
            "sceneView.orthographic, true);"
        ) in handler_source
        assert (
            "sceneView.LookAt(state.pivot, state.rotation, state.size, state.orthographic, true);"
        ) in handler_source


def _extract_parameters(call_args: Any) -> dict:
    if call_args.kwargs.get("parameters") is not None:
        return call_args.kwargs["parameters"]
    if len(call_args.args) >= 2:
        return call_args.args[1]
    return {}

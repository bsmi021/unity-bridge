"""Unit tests for commands/timeline.py — Timeline operations."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from typer.testing import CliRunner

from unity_bridge.commands.timeline import (
    timeline_app,
    timeline_create_clip,
    timeline_create_track,
    timeline_delete_clip,
    timeline_evaluate,
    timeline_get_clips,
    timeline_get_info,
)
from unity_bridge.core.bridge import CommandResult
from unity_bridge.core.output import OutputFormatter

# ---------------------------------------------------------------------------
# create-track
# ---------------------------------------------------------------------------


class TestCreateTrack:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await timeline_create_track(
            mock_bridge, "Assets/Timelines/Cutscene.playable", "AnimationTrack"
        )
        assert (
            _extract_command_type(mock_bridge.send_command_with_retry.call_args)
            == "timeline-operation"
        )

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        await timeline_create_track(
            mock_bridge,
            "Assets/Timelines/Cutscene.playable",
            "AnimationTrack",
            track_name="CameraTrack",
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "create-track"
        assert params["timelineAssetPath"] == "Assets/Timelines/Cutscene.playable"
        assert params["trackType"] == "AnimationTrack"
        assert params["trackName"] == "CameraTrack"

    async def test_omits_track_name_when_not_provided(self, mock_bridge: MagicMock) -> None:
        await timeline_create_track(
            mock_bridge, "Assets/Timelines/Cutscene.playable", "AnimationTrack"
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "trackName" not in params

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        await timeline_create_track(
            mock_bridge, "Assets/Timelines/Cutscene.playable", "AnimationTrack"
        )
        assert _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout") == 30.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        expected = CommandResult(
            success=True,
            data={"operation": "create-track", "trackIndex": 0, "success": True},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await timeline_create_track(
            mock_bridge, "Assets/Timelines/Cutscene.playable", "AnimationTrack"
        )
        assert result.success is True
        assert result.data["trackIndex"] == 0


class TestCreateTrackCli:
    def test_cli_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        result = _run_timeline(
            [
                "create-track",
                "Assets/Timelines/Cutscene.playable",
                "AnimationTrack",
                "--track-name",
                "CameraTrack",
            ],
            mock_bridge,
        )
        assert result.exit_code == 0
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "create-track"
        assert params["trackType"] == "AnimationTrack"
        assert params["trackName"] == "CameraTrack"

    def test_cli_omits_track_name_when_not_provided(self, mock_bridge: MagicMock) -> None:
        result = _run_timeline(
            ["create-track", "Assets/Timelines/Cutscene.playable", "AnimationTrack"],
            mock_bridge,
        )
        assert result.exit_code == 0
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "trackName" not in params


# ---------------------------------------------------------------------------
# create-clip
# ---------------------------------------------------------------------------


class TestCreateClip:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await timeline_create_clip(mock_bridge, "Assets/Timelines/Cutscene.playable", 0)
        assert (
            _extract_command_type(mock_bridge.send_command_with_retry.call_args)
            == "timeline-operation"
        )

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        await timeline_create_clip(
            mock_bridge,
            "Assets/Timelines/Cutscene.playable",
            0,
            clip_asset_path="Assets/Clips/Wave.anim",
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "create-clip"
        assert params["timelineAssetPath"] == "Assets/Timelines/Cutscene.playable"
        assert params["trackIndex"] == 0
        assert params["clipAssetPath"] == "Assets/Clips/Wave.anim"

    async def test_omits_clip_asset_path_when_not_provided(self, mock_bridge: MagicMock) -> None:
        await timeline_create_clip(mock_bridge, "Assets/Timelines/Cutscene.playable", 1)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "clipAssetPath" not in params
        assert params["trackIndex"] == 1


class TestCreateClipCli:
    def test_cli_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        result = _run_timeline(
            [
                "create-clip",
                "Assets/Timelines/Cutscene.playable",
                "0",
                "--clip-asset-path",
                "Assets/Clips/Wave.anim",
            ],
            mock_bridge,
        )
        assert result.exit_code == 0
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "create-clip"
        assert params["trackIndex"] == 0
        assert params["clipAssetPath"] == "Assets/Clips/Wave.anim"

    def test_cli_omits_clip_asset_path_when_not_provided(self, mock_bridge: MagicMock) -> None:
        result = _run_timeline(
            ["create-clip", "Assets/Timelines/Cutscene.playable", "1"], mock_bridge
        )
        assert result.exit_code == 0
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "clipAssetPath" not in params


# ---------------------------------------------------------------------------
# get-clips
# ---------------------------------------------------------------------------


class TestGetClips:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        await timeline_get_clips(mock_bridge, "Assets/Timelines/Cutscene.playable", 0)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {
            "operation": "get-clips",
            "timelineAssetPath": "Assets/Timelines/Cutscene.playable",
            "trackIndex": 0,
        }

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        await timeline_get_clips(mock_bridge, "Assets/Timelines/Cutscene.playable", 0)
        assert _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout") == 10.0

    async def test_returns_clip_data(self, mock_bridge: MagicMock) -> None:
        expected = CommandResult(
            success=True,
            data={
                "operation": "get-clips",
                "clips": [
                    {"clipIndex": 0, "displayName": "Clip 1", "start": 0.0, "duration": 2.0},
                    {"clipIndex": 1, "displayName": "Clip 2", "start": 2.0, "duration": 1.5},
                ],
                "success": True,
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await timeline_get_clips(mock_bridge, "Assets/Timelines/Cutscene.playable", 0)
        assert len(result.data["clips"]) == 2


class TestGetClipsCli:
    def test_cli_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        result = _run_timeline(
            ["get-clips", "Assets/Timelines/Cutscene.playable", "0"], mock_bridge
        )
        assert result.exit_code == 0
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {
            "operation": "get-clips",
            "timelineAssetPath": "Assets/Timelines/Cutscene.playable",
            "trackIndex": 0,
        }


# ---------------------------------------------------------------------------
# delete-clip
# ---------------------------------------------------------------------------


class TestDeleteClip:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await timeline_delete_clip(mock_bridge, "Assets/Timelines/Cutscene.playable", 0, 1)
        assert (
            _extract_command_type(mock_bridge.send_command_with_retry.call_args)
            == "timeline-operation"
        )

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        await timeline_delete_clip(mock_bridge, "Assets/Timelines/Cutscene.playable", 2, 3)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {
            "operation": "delete-clip",
            "timelineAssetPath": "Assets/Timelines/Cutscene.playable",
            "trackIndex": 2,
            "clipIndex": 3,
        }


class TestDeleteClipCli:
    def test_cli_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        result = _run_timeline(
            ["delete-clip", "Assets/Timelines/Cutscene.playable", "2", "3"], mock_bridge
        )
        assert result.exit_code == 0
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {
            "operation": "delete-clip",
            "timelineAssetPath": "Assets/Timelines/Cutscene.playable",
            "trackIndex": 2,
            "clipIndex": 3,
        }


# ---------------------------------------------------------------------------
# get-info
# ---------------------------------------------------------------------------


class TestGetInfo:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        await timeline_get_info(mock_bridge, "Assets/Timelines/Cutscene.playable")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {
            "operation": "get-info",
            "timelineAssetPath": "Assets/Timelines/Cutscene.playable",
        }

    async def test_returns_track_data(self, mock_bridge: MagicMock) -> None:
        expected = CommandResult(
            success=True,
            data={
                "operation": "get-info",
                "tracks": [
                    {
                        "trackIndex": 0,
                        "name": "Animation",
                        "type": "AnimationTrack",
                        "clipCount": 2,
                    }
                ],
                "success": True,
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await timeline_get_info(mock_bridge, "Assets/Timelines/Cutscene.playable")
        assert len(result.data["tracks"]) == 1


class TestGetInfoCli:
    def test_cli_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        result = _run_timeline(["get-info", "Assets/Timelines/Cutscene.playable"], mock_bridge)
        assert result.exit_code == 0
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {
            "operation": "get-info",
            "timelineAssetPath": "Assets/Timelines/Cutscene.playable",
        }


# ---------------------------------------------------------------------------
# evaluate
# ---------------------------------------------------------------------------


class TestEvaluate:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await timeline_evaluate(mock_bridge, "Director/Cutscene")
        assert (
            _extract_command_type(mock_bridge.send_command_with_retry.call_args)
            == "timeline-operation"
        )

    async def test_sends_minimal_parameters(self, mock_bridge: MagicMock) -> None:
        await timeline_evaluate(mock_bridge, "Director/Cutscene")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {
            "operation": "evaluate",
            "directorPath": "Director/Cutscene",
        }

    async def test_sends_time_and_timeline_asset_path(self, mock_bridge: MagicMock) -> None:
        await timeline_evaluate(
            mock_bridge,
            "Director/Cutscene",
            time=1.5,
            timeline_asset_path="Assets/Timelines/Cutscene.playable",
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "evaluate"
        assert params["directorPath"] == "Director/Cutscene"
        assert params["time"] == 1.5
        assert params["timelineAssetPath"] == "Assets/Timelines/Cutscene.playable"

    async def test_omits_optional_params_when_not_provided(self, mock_bridge: MagicMock) -> None:
        await timeline_evaluate(mock_bridge, "Director/Cutscene")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "time" not in params
        assert "timelineAssetPath" not in params

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        await timeline_evaluate(mock_bridge, "Director/Cutscene")
        assert _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout") == 15.0


class TestEvaluateCli:
    def test_cli_sends_minimal_parameters(self, mock_bridge: MagicMock) -> None:
        result = _run_timeline(["evaluate", "Director/Cutscene"], mock_bridge)
        assert result.exit_code == 0
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {
            "operation": "evaluate",
            "directorPath": "Director/Cutscene",
        }

    def test_cli_sends_time_and_timeline_asset_path(self, mock_bridge: MagicMock) -> None:
        result = _run_timeline(
            [
                "evaluate",
                "Director/Cutscene",
                "--time",
                "1.5",
                "--timeline-asset-path",
                "Assets/Timelines/Cutscene.playable",
            ],
            mock_bridge,
        )
        assert result.exit_code == 0
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["time"] == 1.5
        assert params["timelineAssetPath"] == "Assets/Timelines/Cutscene.playable"


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


def _state(mock_bridge: MagicMock) -> SimpleNamespace:
    return SimpleNamespace(bridge=mock_bridge, formatter=OutputFormatter())


def _run_timeline(args: list[str], mock_bridge: MagicMock):
    runner = CliRunner()
    return runner.invoke(timeline_app, args, obj=_state(mock_bridge))

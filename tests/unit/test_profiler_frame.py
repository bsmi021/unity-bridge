"""Unit tests for commands/profiler_frame.py — per-frame profiler drill-down."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from typer.testing import CliRunner

from unity_bridge.core.output import OutputFormatter

ROOT = Path(__file__).resolve().parents[2]


def _import_profiler_frame():
    from unity_bridge.commands import profiler_frame

    return profiler_frame


class TestProfilerFramePayloads:
    async def test_capture_start(self, mock_bridge: MagicMock) -> None:
        mod = _import_profiler_frame()

        await mod.profiler_capture_start(mock_bridge, frame_count=60, log_file="profile.raw")

        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {
            "operation": "capture-start",
            "frameCount": 60,
            "logFile": "profile.raw",
        }

    async def test_capture_stop(self, mock_bridge: MagicMock) -> None:
        mod = _import_profiler_frame()

        await mod.profiler_capture_stop(mock_bridge)

        assert _extract_parameters(mock_bridge.send_command_with_retry.call_args) == {
            "operation": "capture-stop"
        }

    async def test_frame_range(self, mock_bridge: MagicMock) -> None:
        mod = _import_profiler_frame()

        await mod.profiler_frame_range(mock_bridge)

        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "profiler-frame"
        assert _extract_parameters(call_args) == {"operation": "frame-range"}

    async def test_top_time_samples(self, mock_bridge: MagicMock) -> None:
        mod = _import_profiler_frame()

        await mod.profiler_top_time_samples(mock_bridge, frame_index=12, count=5, thread_index=1)

        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {
            "operation": "top-time-samples",
            "frameIndex": 12,
            "count": 5,
            "threadIndex": 1,
        }

    async def test_self_time_samples(self, mock_bridge: MagicMock) -> None:
        mod = _import_profiler_frame()

        await mod.profiler_self_time_samples(mock_bridge, frame_index=12, count=5, thread_index=1)

        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {
            "operation": "self-time-samples",
            "frameIndex": 12,
            "count": 5,
            "threadIndex": 1,
        }

    async def test_sample_time_summary(self, mock_bridge: MagicMock) -> None:
        mod = _import_profiler_frame()

        await mod.profiler_sample_time_summary(
            mock_bridge,
            marker_name="PlayerLoop",
            frame_index_start=10,
            frame_index_end=20,
        )

        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "sample-time-summary"
        assert params["markerName"] == "PlayerLoop"
        assert params["frameIndexStart"] == 10
        assert params["frameIndexEnd"] == 20

    async def test_bottom_up_tree(self, mock_bridge: MagicMock) -> None:
        mod = _import_profiler_frame()

        await mod.profiler_bottom_up_tree(
            mock_bridge,
            frame_index=7,
            marker_name="PlayerLoop",
            depth=4,
            thread_index=1,
        )

        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "bottom-up-tree"
        assert params["frameIndex"] == 7
        assert params["markerName"] == "PlayerLoop"
        assert params["depth"] == 4
        assert params["threadIndex"] == 1

    async def test_gc_alloc_frame(self, mock_bridge: MagicMock) -> None:
        mod = _import_profiler_frame()

        await mod.profiler_gc_alloc(mock_bridge, frame_index=4)

        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "gc-alloc", "frameIndex": 4}

    async def test_sample_gc_alloc(self, mock_bridge: MagicMock) -> None:
        mod = _import_profiler_frame()

        await mod.profiler_sample_gc_alloc(
            mock_bridge,
            frame_index=4,
            marker_name="PlayerLoop",
            thread_index=1,
        )

        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {
            "operation": "sample-gc-alloc",
            "frameIndex": 4,
            "markerName": "PlayerLoop",
            "threadIndex": 1,
        }

    async def test_clear(self, mock_bridge: MagicMock) -> None:
        mod = _import_profiler_frame()

        await mod.profiler_clear(mock_bridge)

        assert _extract_parameters(mock_bridge.send_command_with_retry.call_args) == {
            "operation": "clear"
        }


class TestProfilerFrameCli:
    def test_cli_exposes_full_command_set(self) -> None:
        mod = _import_profiler_frame()

        result = CliRunner().invoke(mod.profiler_frame_app, ["--help"])

        assert result.exit_code == 0
        for command in [
            "capture-start",
            "capture-stop",
            "frame-range",
            "top-time-samples",
            "self-time-samples",
            "sample-time-summary",
            "bottom-up-tree",
            "gc-alloc",
            "sample-gc-alloc",
            "clear",
        ]:
            assert command in result.output

    def test_top_time_cli(self, mock_bridge: MagicMock) -> None:
        mod = _import_profiler_frame()

        result = CliRunner().invoke(
            mod.profiler_frame_app,
            ["top-time-samples", "7", "--count", "3", "--thread-index", "1"],
            obj=_state(mock_bridge),
        )

        assert result.exit_code == 0
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["frameIndex"] == 7
        assert params["count"] == 3
        assert params["threadIndex"] == 1


class TestProfilerFrameBridgeSource:
    def test_csharp_handler_uses_frame_views_and_avoids_obsolete_instance_id(self) -> None:
        handler = ROOT / "ClaudeCodeBridge" / "ProfilerFrameCommandHandler.cs"
        models = ROOT / "ClaudeCodeBridge" / "ProfilerFrameModels.cs"
        registry = ROOT / "ClaudeCodeBridge" / "BridgeCommandRegistry.cs"

        assert handler.is_file()
        handler_source = handler.read_text(encoding="utf-8")
        model_source = models.read_text(encoding="utf-8")
        registry_source = registry.read_text(encoding="utf-8")

        assert 'CommandType => "profiler-frame"' in handler_source
        assert "ProfilerDriver.GetRawFrameDataView" in handler_source
        assert "ProfilerDriver.GetHierarchyFrameDataView" in handler_source
        assert "GetItemColumnDataAsDouble" in handler_source
        assert "columnGcMemory" in handler_source
        assert "GetItemInstanceID" not in handler_source
        assert "ProfilerFrameSampleInfo" in model_source
        assert "new ProfilerFrameCommandHandler()" in registry_source


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


def _state(mock_bridge: MagicMock):
    return type(
        "State",
        (),
        {
            "bridge": mock_bridge,
            "formatter": OutputFormatter(),
        },
    )()

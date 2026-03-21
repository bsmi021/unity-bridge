"""Unit tests for commands/audio_settings.py — audio settings operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from unity_bridge.core.bridge import CommandResult


def _import_mod():
    from unity_bridge.commands import audio_settings

    return audio_settings


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


class TestAudioGet:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.audio_get(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "audio-settings"

    async def test_sends_get_operation(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.audio_get(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params == {"operation": "get"}

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.audio_get(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 10.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        expected = CommandResult(
            success=True,
            data={
                "operation": "get",
                "outputSampleRate": 48000,
                "speakerMode": "Stereo",
                "globalVolume": 1.0,
                "success": True,
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.audio_get(mock_bridge)
        assert result.success is True
        assert result.data["outputSampleRate"] == 48000


# ---------------------------------------------------------------------------
# set
# ---------------------------------------------------------------------------


class TestAudioSet:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.audio_set(mock_bridge, volume=0.8)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "audio-settings"

    async def test_builds_volume_params(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.audio_set(mock_bridge, volume=0.5)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "set"
        assert params["globalVolume"] == pytest.approx(0.5)
        assert params["setGlobalVolume"] is True

    async def test_builds_speaker_mode_params(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.audio_set(mock_bridge, speaker_mode="Stereo")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["speakerMode"] == "Stereo"
        assert params["setSpeakerMode"] is True

    async def test_builds_dsp_buffer_params(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.audio_set(mock_bridge, dsp_buffer_size=1024)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["dspBufferSize"] == 1024
        assert params["setDspBufferSize"] is True

    async def test_omits_unset_params(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.audio_set(mock_bridge, volume=0.8)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert "speakerMode" not in params
        assert "dspBufferSize" not in params

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.audio_set(mock_bridge, volume=1.0)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 15.0


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

"""Audio settings commands: get and set Unity AudioSettings properties."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge
from unity_bridge.core.settings_params import SettingField, build_set_params

_AUDIO_FIELDS = [
    SettingField("volume", ("globalVolume",), "setGlobalVolume"),
    SettingField("pause", ("globalPause",), "setGlobalPause"),
    SettingField("speaker_mode", ("speakerMode",), "setSpeakerMode"),
    SettingField("dsp_buffer_size", ("dspBufferSize",), "setDspBufferSize"),
    SettingField("sample_rate", ("outputSampleRate",), "setOutputSampleRate"),
]

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def audio_get(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """Get current audio settings.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="audio-settings",
        parameters={"operation": "get"},
        timeout=timeout,
    )


async def audio_set(
    bridge: DirectBridge,
    volume: float | None = None,
    pause: bool | None = None,
    speaker_mode: str | None = None,
    dsp_buffer_size: int | None = None,
    sample_rate: int | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Set audio configuration values.

    Args:
        bridge: Active bridge connection.
        volume: Global AudioListener volume (0-1).
        pause: Global AudioListener pause state.
        speaker_mode: AudioSpeakerMode enum value.
        dsp_buffer_size: DSP buffer size.
        sample_rate: Output sample rate.
        timeout: Timeout in seconds.
    """
    params = build_set_params("set", _AUDIO_FIELDS, locals())
    return await bridge.send_command_with_retry(
        command_type="audio-settings",
        parameters=params,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

audio_app = typer.Typer(name="audio", help="Unity audio settings commands.")


@audio_app.command("get")
def audio_get_cli(ctx: typer.Context) -> None:
    """Get current audio settings."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(audio_get(state.bridge))
    print_result(result, state.formatter)


@audio_app.command("set")
def audio_set_cli(
    ctx: typer.Context,
    volume: Annotated[
        float | None,
        typer.Option("--volume", "-v", help="Global volume (0-1)."),
    ] = None,
    speaker_mode: Annotated[
        str | None,
        typer.Option("--speaker-mode", help="AudioSpeakerMode enum."),
    ] = None,
    dsp_buffer: Annotated[
        int | None,
        typer.Option("--dsp-buffer", help="DSP buffer size."),
    ] = None,
) -> None:
    """Set audio configuration values."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        audio_set(
            state.bridge,
            volume=volume,
            speaker_mode=speaker_mode,
            dsp_buffer_size=dsp_buffer,
        )
    )
    print_result(result, state.formatter)

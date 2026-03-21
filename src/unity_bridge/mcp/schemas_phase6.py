"""MCP tool input schemas for Unity Bridge (part 6: Settings & Configuration Gaps).

Phase 6 schemas: time-settings, graphics-settings, environment-settings,
audio-settings, lightmap set-settings extension.
Split from schemas_phase5.py to stay under 500 LOC.
"""

from __future__ import annotations

from typing import Any


def time_settings() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["get", "set"],
                "description": "Time settings operation to perform",
            },
            "fixedDeltaTime": {
                "type": "number",
                "description": "Fixed timestep (default 0.02)",
            },
            "setFixedDeltaTime": {
                "type": "boolean",
                "description": "Flag to apply fixedDeltaTime",
            },
            "maximumDeltaTime": {
                "type": "number",
                "description": "Maximum allowed timestep",
            },
            "setMaximumDeltaTime": {
                "type": "boolean",
                "description": "Flag to apply maximumDeltaTime",
            },
            "timeScale": {
                "type": "number",
                "description": "Time scale factor (1.0 = normal)",
            },
            "setTimeScale": {
                "type": "boolean",
                "description": "Flag to apply timeScale",
            },
            "maximumParticleDeltaTime": {
                "type": "number",
                "description": "Maximum particle timestep",
            },
            "setMaximumParticleDeltaTime": {
                "type": "boolean",
                "description": "Flag to apply maximumParticleDeltaTime",
            },
            "captureDeltaTime": {
                "type": "number",
                "description": "Capture framerate timestep (0 = variable)",
            },
            "setCaptureDeltaTime": {
                "type": "boolean",
                "description": "Flag to apply captureDeltaTime",
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["operation"],
    }


def graphics_settings() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["get", "set"],
                "description": "Graphics settings operation to perform",
            },
            "defaultRenderPipeline": {
                "type": "string",
                "description": (
                    "Asset path to RenderPipelineAsset, 'none' for built-in, or empty to skip"
                ),
            },
            "transparencySortMode": {
                "type": "string",
                "description": "TransparencySortMode enum value",
            },
            "setTransparencySortMode": {
                "type": "boolean",
                "description": "Flag to apply transparencySortMode",
            },
            "useScriptableRenderPipelineBatching": {
                "type": "boolean",
                "description": "Enable/disable SRP batching",
            },
            "setSrpBatching": {
                "type": "boolean",
                "description": "Flag to apply SRP batching change",
            },
            "logWhenShaderIsCompiled": {
                "type": "boolean",
                "description": "Log when shaders are compiled",
            },
            "setLogShaderCompilation": {
                "type": "boolean",
                "description": "Flag to apply shader log change",
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["operation"],
    }


def environment_settings() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["get", "set"],
                "description": "Environment settings operation to perform",
            },
            "skyboxMaterial": {
                "type": "string",
                "description": "Skybox material path or 'none'",
            },
            "ambientMode": {
                "type": "string",
                "description": "AmbientMode: Skybox, Trilight, Flat, Custom",
            },
            "setAmbientMode": {
                "type": "boolean",
                "description": "Flag to apply ambientMode",
            },
            "ambientIntensity": {
                "type": "number",
                "description": "Ambient intensity multiplier",
            },
            "setAmbientIntensity": {
                "type": "boolean",
                "description": "Flag to apply ambientIntensity",
            },
            "fog": {
                "type": "boolean",
                "description": "Enable or disable fog",
            },
            "setFog": {
                "type": "boolean",
                "description": "Flag to apply fog toggle",
            },
            "fogMode": {
                "type": "string",
                "description": "FogMode: Linear, Exponential, ExponentialSquared",
            },
            "setFogMode": {
                "type": "boolean",
                "description": "Flag to apply fogMode",
            },
            "fogColorR": {
                "type": "number",
                "description": "Fog color red component (0-1)",
            },
            "fogColorG": {
                "type": "number",
                "description": "Fog color green component (0-1)",
            },
            "fogColorB": {
                "type": "number",
                "description": "Fog color blue component (0-1)",
            },
            "setFogColor": {
                "type": "boolean",
                "description": "Flag to apply fog color",
            },
            "fogDensity": {
                "type": "number",
                "description": "Fog density for exponential modes",
            },
            "setFogDensity": {
                "type": "boolean",
                "description": "Flag to apply fogDensity",
            },
            "fogStartDistance": {
                "type": "number",
                "description": "Fog start distance (linear mode)",
            },
            "setFogStartDistance": {
                "type": "boolean",
                "description": "Flag to apply fogStartDistance",
            },
            "fogEndDistance": {
                "type": "number",
                "description": "Fog end distance (linear mode)",
            },
            "setFogEndDistance": {
                "type": "boolean",
                "description": "Flag to apply fogEndDistance",
            },
            "reflectionBounces": {
                "type": "integer",
                "description": "Reflection probe bounce count",
            },
            "setReflectionBounces": {
                "type": "boolean",
                "description": "Flag to apply reflectionBounces",
            },
            "reflectionIntensity": {
                "type": "number",
                "description": "Reflection intensity multiplier",
            },
            "setReflectionIntensity": {
                "type": "boolean",
                "description": "Flag to apply reflectionIntensity",
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["operation"],
    }


def audio_settings() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["get", "set"],
                "description": "Audio settings operation to perform",
            },
            "globalVolume": {
                "type": "number",
                "description": "Global AudioListener volume (0-1)",
            },
            "setGlobalVolume": {
                "type": "boolean",
                "description": "Flag to apply globalVolume",
            },
            "globalPause": {
                "type": "boolean",
                "description": "Global AudioListener pause state",
            },
            "setGlobalPause": {
                "type": "boolean",
                "description": "Flag to apply globalPause",
            },
            "speakerMode": {
                "type": "string",
                "description": "AudioSpeakerMode enum value",
            },
            "setSpeakerMode": {
                "type": "boolean",
                "description": "Flag to apply speakerMode",
            },
            "dspBufferSize": {
                "type": "integer",
                "description": "DSP buffer size",
            },
            "setDspBufferSize": {
                "type": "boolean",
                "description": "Flag to apply dspBufferSize",
            },
            "outputSampleRate": {
                "type": "integer",
                "description": "Output sample rate",
            },
            "setOutputSampleRate": {
                "type": "boolean",
                "description": "Flag to apply outputSampleRate",
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["operation"],
    }

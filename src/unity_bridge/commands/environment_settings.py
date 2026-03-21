"""Environment settings commands: lighting, fog, and reflection."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_color(value: str) -> tuple[float, float, float]:
    """Parse 'R,G,B' color string (0-1 range)."""
    parts = value.split(",")
    if len(parts) != 3:
        raise typer.BadParameter(f"Expected R,G,B format, got '{value}'")
    try:
        return (float(parts[0]), float(parts[1]), float(parts[2]))
    except ValueError:
        raise typer.BadParameter(f"Non-numeric value in '{value}'")


# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def environment_get(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """Get current environment settings.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="environment-settings",
        parameters={"operation": "get"},
        timeout=timeout,
    )


async def environment_set(
    bridge: DirectBridge,
    skybox_material: str | None = None,
    ambient_mode: str | None = None,
    ambient_intensity: float | None = None,
    ambient_light: tuple[float, float, float] | None = None,
    fog: bool | None = None,
    fog_mode: str | None = None,
    fog_color: tuple[float, float, float] | None = None,
    fog_density: float | None = None,
    fog_start: float | None = None,
    fog_end: float | None = None,
    reflection_bounces: int | None = None,
    reflection_intensity: float | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Set environment configuration values.

    Args:
        bridge: Active bridge connection.
        skybox_material: Asset path to skybox material, or 'none'.
        ambient_mode: AmbientMode enum (Skybox, Trilight, Flat, Custom).
        ambient_intensity: Ambient intensity multiplier.
        ambient_light: Flat ambient color as (r, g, b) 0-1.
        fog: Enable or disable fog.
        fog_mode: FogMode enum (Linear, Exponential, ExponentialSquared).
        fog_color: Fog color as (r, g, b) 0-1.
        fog_density: Fog density (for exponential modes).
        fog_start: Fog start distance (for linear).
        fog_end: Fog end distance (for linear).
        reflection_bounces: Number of reflection bounces.
        reflection_intensity: Reflection intensity multiplier.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {"operation": "set"}

    if skybox_material is not None:
        params["skyboxMaterial"] = skybox_material
    if ambient_mode is not None:
        params["ambientMode"] = ambient_mode
        params["setAmbientMode"] = True
    if ambient_intensity is not None:
        params["ambientIntensity"] = ambient_intensity
        params["setAmbientIntensity"] = True
    if ambient_light is not None:
        params["ambientLightR"] = ambient_light[0]
        params["ambientLightG"] = ambient_light[1]
        params["ambientLightB"] = ambient_light[2]
        params["setAmbientLight"] = True
    if fog is not None:
        params["fog"] = fog
        params["setFog"] = True
    if fog_mode is not None:
        params["fogMode"] = fog_mode
        params["setFogMode"] = True
    if fog_color is not None:
        params["fogColorR"] = fog_color[0]
        params["fogColorG"] = fog_color[1]
        params["fogColorB"] = fog_color[2]
        params["setFogColor"] = True
    if fog_density is not None:
        params["fogDensity"] = fog_density
        params["setFogDensity"] = True
    if fog_start is not None:
        params["fogStartDistance"] = fog_start
        params["setFogStartDistance"] = True
    if fog_end is not None:
        params["fogEndDistance"] = fog_end
        params["setFogEndDistance"] = True
    if reflection_bounces is not None:
        params["reflectionBounces"] = reflection_bounces
        params["setReflectionBounces"] = True
    if reflection_intensity is not None:
        params["reflectionIntensity"] = reflection_intensity
        params["setReflectionIntensity"] = True

    return await bridge.send_command_with_retry(
        command_type="environment-settings",
        parameters=params,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

environment_app = typer.Typer(name="environment", help="Environment lighting, fog, and reflection.")


@environment_app.command("get")
def environment_get_cli(ctx: typer.Context) -> None:
    """Get current environment settings."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(environment_get(state.bridge))
    print_result(result, state.formatter)


@environment_app.command("set")
def environment_set_cli(
    ctx: typer.Context,
    fog_flag: Annotated[
        bool | None,
        typer.Option("--fog/--no-fog", help="Enable or disable fog."),
    ] = None,
    fog_color: Annotated[
        str | None,
        typer.Option("--fog-color", help="Fog color as R,G,B (0-1)."),
    ] = None,
    fog_density: Annotated[
        float | None,
        typer.Option("--fog-density", help="Fog density."),
    ] = None,
    ambient_intensity: Annotated[
        float | None,
        typer.Option("--ambient-intensity", help="Ambient intensity."),
    ] = None,
    skybox: Annotated[
        str | None,
        typer.Option("--skybox", help="Skybox material path or 'none'."),
    ] = None,
) -> None:
    """Set environment configuration values."""
    from unity_bridge.core.output import print_result

    parsed_fog_color = _parse_color(fog_color) if fog_color else None
    state = ctx.obj
    result = asyncio.run(
        environment_set(
            state.bridge,
            skybox_material=skybox,
            ambient_intensity=ambient_intensity,
            fog=fog_flag,
            fog_color=parsed_fog_color,
            fog_density=fog_density,
        )
    )
    print_result(result, state.formatter)

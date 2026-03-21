"""Preset management commands: create, apply, can-apply, list-defaults."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def preset_create(
    bridge: DirectBridge,
    source_path: str,
    output_path: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Create a preset from an existing asset.

    Args:
        bridge: Active bridge connection.
        source_path: Asset path of the source object.
        output_path: Where to save the preset asset.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="preset-operation",
        parameters={
            "operation": "create",
            "sourcePath": source_path,
            "outputPath": output_path,
        },
        timeout=timeout,
    )


async def preset_apply(
    bridge: DirectBridge,
    preset_path: str,
    target_path: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Apply a preset to a target asset.

    Args:
        bridge: Active bridge connection.
        preset_path: Asset path of the preset.
        target_path: Asset path of the target.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="preset-operation",
        parameters={
            "operation": "apply",
            "presetPath": preset_path,
            "targetPath": target_path,
        },
        timeout=timeout,
    )


async def preset_can_apply(
    bridge: DirectBridge,
    preset_path: str,
    target_path: str,
    timeout: float = 10.0,
) -> CommandResult:
    """Check if a preset can be applied to a target asset.

    Args:
        bridge: Active bridge connection.
        preset_path: Asset path of the preset.
        target_path: Asset path of the target.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="preset-operation",
        parameters={
            "operation": "can-apply",
            "presetPath": preset_path,
            "targetPath": target_path,
        },
        timeout=timeout,
    )


async def preset_list_defaults(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """List all default presets.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="preset-operation",
        parameters={"operation": "list-defaults"},
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrapper
# ---------------------------------------------------------------------------

preset_app = typer.Typer(name="preset", help="Unity Preset management.")


@preset_app.command("create")
def preset_create_cli(
    ctx: typer.Context,
    source: Annotated[str, typer.Argument(help="Source asset path.")],
    output: Annotated[str, typer.Argument(help="Output preset path.")],
) -> None:
    """Create a preset from an existing asset."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(preset_create(state.bridge, source, output))
    print_result(result, state.formatter)


@preset_app.command("apply")
def preset_apply_cli(
    ctx: typer.Context,
    preset_path: Annotated[str, typer.Argument(help="Preset asset path.")],
    target: Annotated[str, typer.Argument(help="Target asset path.")],
) -> None:
    """Apply a preset to a target asset."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(preset_apply(state.bridge, preset_path, target))
    print_result(result, state.formatter)


@preset_app.command("can-apply")
def preset_can_apply_cli(
    ctx: typer.Context,
    preset_path: Annotated[str, typer.Argument(help="Preset asset path.")],
    target: Annotated[str, typer.Argument(help="Target asset path.")],
) -> None:
    """Check if a preset is compatible with a target asset."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(preset_can_apply(state.bridge, preset_path, target))
    print_result(result, state.formatter)


@preset_app.command("list-defaults")
def preset_list_defaults_cli(ctx: typer.Context) -> None:
    """List all default presets."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(preset_list_defaults(state.bridge))
    print_result(result, state.formatter)

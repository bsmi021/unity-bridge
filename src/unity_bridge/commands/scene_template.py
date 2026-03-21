"""Scene template commands: list, create-from-scene, instantiate."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def scene_template_list(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """List available scene templates.

    Args:
        bridge: Active bridge connection.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="scene-template",
        parameters={"operation": "list"},
        timeout=timeout,
    )


async def scene_template_create(
    bridge: DirectBridge,
    scene_path: str,
    output_path: str,
    timeout: float = 30.0,
) -> CommandResult:
    """Create a scene template from a scene file.

    Args:
        bridge: Active bridge connection.
        scene_path: Path to the source scene (.unity).
        output_path: Where to save the template asset.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="scene-template",
        parameters={
            "operation": "create-from-scene",
            "scenePath": scene_path,
            "outputPath": output_path,
        },
        timeout=timeout,
    )


async def scene_template_instantiate(
    bridge: DirectBridge,
    template_path: str,
    output_path: str | None = None,
    timeout: float = 30.0,
) -> CommandResult:
    """Create a new scene from a template.

    Args:
        bridge: Active bridge connection.
        template_path: Path to the scene template asset.
        output_path: Optional path for the new scene.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {
        "operation": "instantiate",
        "templatePath": template_path,
    }
    if output_path is not None:
        params["outputPath"] = output_path

    return await bridge.send_command_with_retry(
        command_type="scene-template",
        parameters=params,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrapper
# ---------------------------------------------------------------------------

scene_template_app = typer.Typer(
    name="scene-template", help="Scene template operations."
)


@scene_template_app.command("list")
def scene_template_list_cli(ctx: typer.Context) -> None:
    """List available scene templates."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(scene_template_list(state.bridge))
    print_result(result, state.formatter)


@scene_template_app.command("create")
def scene_template_create_cli(
    ctx: typer.Context,
    scene_path: Annotated[str, typer.Argument(help="Source scene path (.unity).")],
    output: Annotated[str, typer.Argument(help="Output template path.")],
) -> None:
    """Create a scene template from a scene file."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(scene_template_create(state.bridge, scene_path, output))
    print_result(result, state.formatter)


@scene_template_app.command("instantiate")
def scene_template_instantiate_cli(
    ctx: typer.Context,
    template: Annotated[str, typer.Argument(help="Template asset path.")],
    output: Annotated[
        str | None,
        typer.Option("--output", "-o", help="Output scene path."),
    ] = None,
) -> None:
    """Create a new scene from a template."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(scene_template_instantiate(state.bridge, template, output))
    print_result(result, state.formatter)

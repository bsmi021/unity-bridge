"""Find references commands: find asset references in loaded scenes."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async function (CLI + MCP)
# ---------------------------------------------------------------------------


async def find_references_in_scene(
    bridge: DirectBridge,
    asset_path: str,
    timeout: float = 30.0,
) -> CommandResult:
    """Find all references to an asset in loaded scenes.

    Iterates all components via SerializedObject/SerializedProperty to find
    ObjectReference properties pointing at the target asset.

    Args:
        bridge: Active bridge connection.
        asset_path: Path to the asset to search for.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="find-references",
        parameters={
            "operation": "find-in-scene",
            "assetPath": asset_path,
        },
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI
# ---------------------------------------------------------------------------


def find_references_cli(
    ctx: typer.Context,
    asset_path: Annotated[str, typer.Argument(help="Asset path to search for.")],
    timeout: Annotated[
        int,
        typer.Option("--timeout", help="Timeout in seconds."),
    ] = 30,
) -> None:
    """Find all references to an asset in loaded scenes."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(find_references_in_scene(state.bridge, asset_path, float(timeout)))
    print_result(result, state.formatter)

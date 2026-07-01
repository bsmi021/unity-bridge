"""VFX commands: VisualEffectAsset inspection (read-only)."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def vfx_get_info(
    bridge: DirectBridge,
    asset_path: str | None = None,
    guid: str | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Get connected event names and exposed properties for a VisualEffectAsset.

    Args:
        bridge: Active bridge connection.
        asset_path: Asset path to the VisualEffectAsset.
        guid: GUID of the VisualEffectAsset (alternative to asset_path).
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {"operation": "get-info"}
    if asset_path is not None:
        params["assetPath"] = asset_path
    if guid is not None:
        params["guid"] = guid

    return await bridge.send_command_with_retry(
        command_type="vfx-asset",
        parameters=params,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

vfx_app = typer.Typer(name="vfx", help="VisualEffectAsset inspection commands.")


@vfx_app.command("get-info")
def vfx_get_info_cli(
    ctx: typer.Context,
    asset_path: Annotated[
        str | None,
        typer.Option("--asset-path", help="Asset path to the VisualEffectAsset."),
    ] = None,
    guid: Annotated[
        str | None,
        typer.Option("--guid", help="GUID of the VisualEffectAsset."),
    ] = None,
) -> None:
    """Get connected event names and exposed properties for a VisualEffectAsset."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(vfx_get_info(state.bridge, asset_path=asset_path, guid=guid))
    print_result(result, state.formatter)

"""Asset commands: find, query, import, refresh."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Valid actions
# ---------------------------------------------------------------------------

VALID_ACTIONS = frozenset({"find", "query", "import", "refresh"})

# ---------------------------------------------------------------------------
# Core async function (CLI + MCP)
# ---------------------------------------------------------------------------


async def asset_operation(
    bridge: DirectBridge,
    action: str,
    path: str | None = None,
    asset_type: str | None = None,
    pattern: str | None = None,
    timeout: float = 60.0,
) -> CommandResult:
    """Perform an asset database operation.

    Args:
        bridge: Active bridge connection.
        action: Operation to perform — ``find``, ``query``, ``import``, or ``refresh``.
        path: Asset path or directory to operate on.
        asset_type: Asset type filter (e.g. ``Material``, ``Prefab``).
        pattern: Search pattern or glob for asset names.
        timeout: Timeout in seconds.

    Raises:
        ValueError: If *action* is not a recognised asset operation.
    """
    normalised = action.lower().strip()
    if normalised not in VALID_ACTIONS:
        raise ValueError(
            f"Invalid asset action '{action}'. Must be one of: {', '.join(sorted(VALID_ACTIONS))}"
        )

    params: dict[str, object] = {"operation": normalised}
    if path is not None:
        params["path"] = path
    if asset_type is not None:
        params["assetType"] = asset_type
    if pattern is not None:
        params["pattern"] = pattern

    return await bridge.send_command_with_retry(
        command_type="asset-operation",
        parameters=params,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrapper
# ---------------------------------------------------------------------------

asset_app = typer.Typer(name="asset", help="Unity asset database commands.")


@asset_app.callback(invoke_without_command=True)
def asset_cli(
    ctx: typer.Context,
    action: Annotated[
        str,
        typer.Argument(help="Asset action: find, query, import, or refresh."),
    ],
    path: Annotated[
        str | None,
        typer.Option("--path", "-p", help="Asset path or directory."),
    ] = None,
    asset_type: Annotated[
        str | None,
        typer.Option("--type", "-t", help="Asset type filter (e.g. Material)."),
    ] = None,
    pattern: Annotated[
        str | None,
        typer.Option("--pattern", help="Search pattern for asset names."),
    ] = None,
) -> None:
    """Perform an asset database operation (find | query | import | refresh)."""
    from unity_bridge.core.output import print_result

    normalised = action.lower().strip()
    if normalised not in VALID_ACTIONS:
        raise typer.BadParameter(
            f"Invalid action '{action}'. Must be one of: {', '.join(sorted(VALID_ACTIONS))}"
        )

    state = ctx.obj
    result = asyncio.run(
        asset_operation(state.bridge, normalised, path, asset_type, pattern)
    )
    print_result(result, state.formatter)

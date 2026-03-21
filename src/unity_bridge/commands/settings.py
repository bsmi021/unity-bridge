"""Settings commands: player settings get/set and scripting defines."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Valid actions
# ---------------------------------------------------------------------------

VALID_ACTIONS = frozenset({"get", "set", "defines-list", "defines-add", "defines-remove"})

# ---------------------------------------------------------------------------
# Core async function (CLI + MCP)
# ---------------------------------------------------------------------------


async def player_settings_operation(
    bridge: DirectBridge,
    action: str,
    key: str | None = None,
    value: str | None = None,
    symbol: str | None = None,
    platform: str | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Perform a player settings operation.

    Args:
        bridge: Active bridge connection.
        action: Operation — ``get``, ``set``, ``defines-list``,
                ``defines-add``, or ``defines-remove``.
        key: Setting key for get/set (e.g. ``companyName``).
        value: New value for set operation.
        symbol: Define symbol for defines-add/defines-remove.
        platform: Named build target (default: active platform).
        timeout: Timeout in seconds.

    Raises:
        ValueError: If *action* is not a recognised operation.
    """
    normalised = action.lower().strip()
    if normalised not in VALID_ACTIONS:
        raise ValueError(
            f"Invalid settings action '{action}'. "
            f"Must be one of: {', '.join(sorted(VALID_ACTIONS))}"
        )

    params: dict[str, object] = {"operation": normalised}
    if key is not None:
        params["key"] = key
    if value is not None:
        params["value"] = value
    if symbol is not None:
        params["symbol"] = symbol
    if platform is not None:
        params["platform"] = platform

    return await bridge.send_command_with_retry(
        command_type="player-settings-operation",
        parameters=params,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrapper
# ---------------------------------------------------------------------------

settings_app = typer.Typer(name="settings", help="Unity player settings commands.")


@settings_app.command("get")
def settings_get(
    ctx: typer.Context,
    key: Annotated[
        str | None,
        typer.Argument(help="Setting key (omit for all settings)."),
    ] = None,
) -> None:
    """Get player settings (all or a specific key)."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(player_settings_operation(state.bridge, "get", key=key))
    print_result(result, state.formatter)


@settings_app.command("set")
def settings_set(
    ctx: typer.Context,
    key: Annotated[str, typer.Argument(help="Setting key to modify.")],
    value: Annotated[str, typer.Argument(help="New value.")],
) -> None:
    """Set a player setting value."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(player_settings_operation(state.bridge, "set", key=key, value=value))
    print_result(result, state.formatter)


@settings_app.command("defines")
def settings_defines(
    ctx: typer.Context,
    action: Annotated[
        str,
        typer.Argument(help="Defines action: list, add, or remove."),
    ],
    symbol: Annotated[
        str | None,
        typer.Option("--symbol", "-s", help="Define symbol (required for add/remove)."),
    ] = None,
    platform: Annotated[
        str | None,
        typer.Option("--platform", "-p", help="Target platform (default: active)."),
    ] = None,
) -> None:
    """Manage scripting define symbols (list | add | remove)."""
    from unity_bridge.core.output import print_result

    action_lower = action.lower().strip()
    if action_lower not in {"list", "add", "remove"}:
        raise typer.BadParameter(
            f"Invalid defines action '{action}'. Must be one of: list, add, remove"
        )

    full_action = f"defines-{action_lower}"
    state = ctx.obj
    result = asyncio.run(
        player_settings_operation(state.bridge, full_action, symbol=symbol, platform=platform)
    )
    print_result(result, state.formatter)

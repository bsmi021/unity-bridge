"""Play mode control: play, pause, stop."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Valid actions
# ---------------------------------------------------------------------------

VALID_ACTIONS = frozenset({"play", "pause", "stop"})

# ---------------------------------------------------------------------------
# Core async function (CLI + MCP)
# ---------------------------------------------------------------------------


async def playmode_control(
    bridge: DirectBridge,
    action: str,
    timeout: float = 10.0,
) -> CommandResult:
    """Control Unity Editor play mode.

    Args:
        bridge: Active bridge connection.
        action: One of ``play``, ``pause``, or ``stop``.
        timeout: Timeout in seconds.

    Raises:
        ValueError: If *action* is not a recognised play-mode action.
    """
    normalised = action.lower().strip()
    if normalised not in VALID_ACTIONS:
        raise ValueError(
            f"Invalid playmode action '{action}'. Must be one of: {', '.join(sorted(VALID_ACTIONS))}"
        )

    return await bridge.send_command_with_retry(
        command_type="playmode-control",
        parameters={"action": normalised},
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrapper
# ---------------------------------------------------------------------------

playmode_app = typer.Typer(name="playmode", help="Unity Editor play mode control.")


@playmode_app.callback(invoke_without_command=True)
def playmode_cli(
    ctx: typer.Context,
    action: Annotated[
        str,
        typer.Argument(help="Play mode action: play, pause, or stop."),
    ],
) -> None:
    """Control Unity play mode (play | pause | stop)."""
    from unity_bridge.core.output import print_result

    if action.lower().strip() not in VALID_ACTIONS:
        raise typer.BadParameter(
            f"Invalid action '{action}'. Must be one of: {', '.join(sorted(VALID_ACTIONS))}"
        )

    state = ctx.obj
    result = asyncio.run(playmode_control(state.bridge, action))
    print_result(result, state.formatter)

"""Animator commands: get-state, set-state, get-params, set-param."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Valid actions
# ---------------------------------------------------------------------------

VALID_ACTIONS = frozenset({"get-state", "set-state", "get-params", "set-param"})

# ---------------------------------------------------------------------------
# Core async function (CLI + MCP)
# ---------------------------------------------------------------------------


async def animator_operation(
    bridge: DirectBridge,
    action: str,
    object_path: str,
    state_name: str | None = None,
    param_name: str | None = None,
    param_value: str | None = None,
    layer: int | None = None,
    timeout: float = 30.0,
) -> CommandResult:
    """Perform an animator operation on a GameObject.

    Args:
        bridge: Active bridge connection.
        action: One of ``get-state``, ``set-state``, ``get-params``, ``set-param``.
        object_path: Hierarchy path to the GameObject with an Animator.
        state_name: State name for set-state operations.
        param_name: Parameter name for set-param operations.
        param_value: Parameter value for set-param (parsed as JSON or string).
        layer: Animator layer index.
        timeout: Timeout in seconds.

    Raises:
        ValueError: If *action* is not a recognised animator operation.
    """
    normalised = action.lower().strip()
    if normalised not in VALID_ACTIONS:
        raise ValueError(
            f"Invalid animator action '{action}'. "
            f"Must be one of: {', '.join(sorted(VALID_ACTIONS))}"
        )

    params: dict[str, object] = {
        "operation": normalised,
        "objectPath": object_path,
    }
    if state_name is not None:
        params["stateName"] = state_name
    if param_name is not None:
        params["paramName"] = param_name
    if param_value is not None:
        params["paramValue"] = _parse_param_value(param_value)
    if layer is not None:
        params["layer"] = layer

    return await bridge.send_command_with_retry(
        command_type="animator-operation",
        parameters=params,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_param_value(raw: str) -> object:
    """Try to parse a parameter value as JSON, falling back to string."""
    import json

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


# ---------------------------------------------------------------------------
# Typer CLI wrapper
# ---------------------------------------------------------------------------

animator_app = typer.Typer(name="animator", help="Animator state and parameter commands.")


@animator_app.callback(invoke_without_command=True)
def animator_cli(
    ctx: typer.Context,
    action: Annotated[
        str,
        typer.Argument(
            help="Animator action: get-state, set-state, get-params, or set-param."
        ),
    ],
    object_path: Annotated[
        str,
        typer.Argument(help="Hierarchy path to the GameObject with Animator."),
    ],
    state_name: Annotated[
        str | None,
        typer.Option("--state-name", help="State name (for set-state)."),
    ] = None,
    param_name: Annotated[
        str | None,
        typer.Option("--param-name", help="Parameter name (for set-param)."),
    ] = None,
    param_value: Annotated[
        str | None,
        typer.Option("--param-value", help="Parameter value (for set-param)."),
    ] = None,
    layer: Annotated[
        int | None,
        typer.Option("--layer", help="Animator layer index."),
    ] = None,
) -> None:
    """Perform an animator operation (get-state | set-state | get-params | set-param)."""
    from unity_bridge.core.output import print_result

    normalised = action.lower().strip()
    if normalised not in VALID_ACTIONS:
        raise typer.BadParameter(
            f"Invalid action '{action}'. "
            f"Must be one of: {', '.join(sorted(VALID_ACTIONS))}"
        )

    state = ctx.obj
    result = asyncio.run(animator_operation(
        state.bridge, normalised, object_path,
        state_name, param_name, param_value, layer,
    ))
    print_result(result, state.formatter)

"""Material commands: modify, create, duplicate."""

from __future__ import annotations

import asyncio
import json as _json
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Valid actions
# ---------------------------------------------------------------------------

VALID_ACTIONS = frozenset({"modify", "create", "duplicate"})

# ---------------------------------------------------------------------------
# Core async function (CLI + MCP)
# ---------------------------------------------------------------------------


async def material_operation(
    bridge: DirectBridge,
    action: str,
    path: str,
    properties: dict[str, object] | None = None,
    timeout: float = 30.0,
) -> CommandResult:
    """Perform a material operation.

    Args:
        bridge: Active bridge connection.
        action: Operation to perform — ``modify``, ``create``, or ``duplicate``.
        path: Material asset path.
        properties: Optional property overrides as a dict.
        timeout: Timeout in seconds.

    Raises:
        ValueError: If *action* is not a recognised material operation.
    """
    normalised = action.lower().strip()
    if normalised not in VALID_ACTIONS:
        raise ValueError(
            f"Invalid material action '{action}'. "
            f"Must be one of: {', '.join(sorted(VALID_ACTIONS))}"
        )

    params: dict[str, object] = {
        "operation": normalised,
        "materialPath": path,
    }
    if properties is not None:
        params["properties"] = properties

    return await bridge.send_command_with_retry(
        command_type="material-operation",
        parameters=params,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_properties(raw: str | None) -> dict[str, object] | None:
    """Parse a JSON string into a properties dict."""
    if raw is None:
        return None
    try:
        parsed = _json.loads(raw)
    except _json.JSONDecodeError as exc:
        raise typer.BadParameter(f"Invalid JSON for --properties: {exc}") from exc
    if not isinstance(parsed, dict):
        raise typer.BadParameter("--properties must be a JSON object (dict).")
    return parsed


# ---------------------------------------------------------------------------
# Typer CLI wrapper
# ---------------------------------------------------------------------------

material_app = typer.Typer(name="material", help="Material management commands.")


@material_app.callback(invoke_without_command=True)
def material_cli(
    ctx: typer.Context,
    action: Annotated[
        str,
        typer.Argument(help="Material action: modify, create, or duplicate."),
    ],
    path: Annotated[
        str,
        typer.Argument(help="Material asset path."),
    ],
    properties: Annotated[
        str | None,
        typer.Option("--properties", help="JSON string of property overrides."),
    ] = None,
) -> None:
    """Perform a material operation (modify | create | duplicate)."""
    from unity_bridge.core.output import print_result

    normalised = action.lower().strip()
    if normalised not in VALID_ACTIONS:
        raise typer.BadParameter(
            f"Invalid action '{action}'. "
            f"Must be one of: {', '.join(sorted(VALID_ACTIONS))}"
        )

    parsed_props = _parse_properties(properties)
    state = ctx.obj
    result = asyncio.run(
        material_operation(state.bridge, normalised, path, parsed_props)
    )
    print_result(result, state.formatter)

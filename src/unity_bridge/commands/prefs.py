"""EditorPrefs and SessionState commands: get, set, delete, has."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def prefs_get(
    bridge: DirectBridge,
    key: str,
    value_type: str = "string",
    scope: str = "prefs",
    timeout: float = 5.0,
) -> CommandResult:
    """Get an EditorPrefs or SessionState value.

    Args:
        bridge: Active bridge connection.
        key: Preference key.
        value_type: Type of value (string, int, float, bool).
        scope: Storage scope (prefs or session).
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="editor-prefs",
        parameters={
            "operation": "get",
            "key": key,
            "valueType": value_type,
            "scope": scope,
        },
        timeout=timeout,
    )


async def prefs_set(
    bridge: DirectBridge,
    key: str,
    value: str,
    value_type: str = "string",
    scope: str = "prefs",
    timeout: float = 5.0,
) -> CommandResult:
    """Set an EditorPrefs or SessionState value.

    Args:
        bridge: Active bridge connection.
        key: Preference key.
        value: Value to set (as string).
        value_type: Type of value (string, int, float, bool).
        scope: Storage scope (prefs or session).
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="editor-prefs",
        parameters={
            "operation": "set",
            "key": key,
            "value": value,
            "valueType": value_type,
            "scope": scope,
        },
        timeout=timeout,
    )


async def prefs_delete(
    bridge: DirectBridge,
    key: str,
    scope: str = "prefs",
    timeout: float = 5.0,
) -> CommandResult:
    """Delete an EditorPrefs or SessionState key.

    Args:
        bridge: Active bridge connection.
        key: Preference key to delete.
        scope: Storage scope (prefs or session).
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="editor-prefs",
        parameters={
            "operation": "delete",
            "key": key,
            "scope": scope,
        },
        timeout=timeout,
    )


async def prefs_has(
    bridge: DirectBridge,
    key: str,
    scope: str = "prefs",
    timeout: float = 5.0,
) -> CommandResult:
    """Check if an EditorPrefs or SessionState key exists.

    Args:
        bridge: Active bridge connection.
        key: Preference key to check.
        scope: Storage scope (prefs or session).
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="editor-prefs",
        parameters={
            "operation": "has",
            "key": key,
            "scope": scope,
        },
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrapper
# ---------------------------------------------------------------------------

prefs_app = typer.Typer(name="prefs", help="EditorPrefs and SessionState commands.")


@prefs_app.command("get")
def prefs_get_cli(
    ctx: typer.Context,
    key: Annotated[str, typer.Argument(help="Preference key.")],
    value_type: Annotated[
        str,
        typer.Option("--type", "-t", help="Value type: string, int, float, bool."),
    ] = "string",
    scope: Annotated[
        str,
        typer.Option("--scope", "-s", help="Storage scope: prefs or session."),
    ] = "prefs",
) -> None:
    """Get an EditorPrefs or SessionState value."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(prefs_get(state.bridge, key, value_type, scope))
    print_result(result, state.formatter)


@prefs_app.command("set")
def prefs_set_cli(
    ctx: typer.Context,
    key: Annotated[str, typer.Argument(help="Preference key.")],
    value: Annotated[str, typer.Argument(help="Value to set.")],
    value_type: Annotated[
        str,
        typer.Option("--type", "-t", help="Value type: string, int, float, bool."),
    ] = "string",
    scope: Annotated[
        str,
        typer.Option("--scope", "-s", help="Storage scope: prefs or session."),
    ] = "prefs",
) -> None:
    """Set an EditorPrefs or SessionState value."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(prefs_set(state.bridge, key, value, value_type, scope))
    print_result(result, state.formatter)


@prefs_app.command("delete")
def prefs_delete_cli(
    ctx: typer.Context,
    key: Annotated[str, typer.Argument(help="Preference key to delete.")],
    scope: Annotated[
        str,
        typer.Option("--scope", "-s", help="Storage scope: prefs or session."),
    ] = "prefs",
) -> None:
    """Delete an EditorPrefs or SessionState key."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(prefs_delete(state.bridge, key, scope))
    print_result(result, state.formatter)


@prefs_app.command("has")
def prefs_has_cli(
    ctx: typer.Context,
    key: Annotated[str, typer.Argument(help="Preference key to check.")],
    scope: Annotated[
        str,
        typer.Option("--scope", "-s", help="Storage scope: prefs or session."),
    ] = "prefs",
) -> None:
    """Check if an EditorPrefs or SessionState key exists."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(prefs_has(state.bridge, key, scope))
    print_result(result, state.formatter)

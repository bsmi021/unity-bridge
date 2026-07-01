"""Material commands: modify, create, duplicate, keyword, render queue, copy."""

from __future__ import annotations

import asyncio
import json as _json
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Valid actions for the legacy operation endpoint
# ---------------------------------------------------------------------------

VALID_ACTIONS = frozenset({"modify", "create", "duplicate"})

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def material_operation(
    bridge: DirectBridge,
    action: str,
    path: str,
    properties: dict[str, object] | None = None,
    timeout: float = 30.0,
) -> CommandResult:
    """Perform a material operation (modify, create, duplicate)."""
    normalised = action.lower().strip()
    if normalised not in VALID_ACTIONS:
        raise ValueError(
            f"Invalid material action '{action}'. "
            f"Must be one of: {', '.join(sorted(VALID_ACTIONS))}"
        )
    params: dict[str, object] = {"operation": normalised, "materialPath": path}
    if properties is not None:
        params["properties"] = properties
    return await bridge.send_command_with_retry(
        command_type="material-operation", parameters=params, timeout=timeout
    )


async def material_enable_keyword(
    bridge: DirectBridge, path: str, keyword: str, timeout: float = 30.0
) -> CommandResult:
    """Enable a shader keyword on a material."""
    return await bridge.send_command_with_retry(
        command_type="material-operation",
        parameters={"operation": "enable-keyword", "materialPath": path, "keyword": keyword},
        timeout=timeout,
    )


async def material_disable_keyword(
    bridge: DirectBridge, path: str, keyword: str, timeout: float = 30.0
) -> CommandResult:
    """Disable a shader keyword on a material."""
    return await bridge.send_command_with_retry(
        command_type="material-operation",
        parameters={"operation": "disable-keyword", "materialPath": path, "keyword": keyword},
        timeout=timeout,
    )


async def material_get_keywords(
    bridge: DirectBridge, path: str, timeout: float = 30.0
) -> CommandResult:
    """Get active shader keywords on a material."""
    return await bridge.send_command_with_retry(
        command_type="material-operation",
        parameters={"operation": "get-keywords", "materialPath": path},
        timeout=timeout,
    )


async def material_set_render_queue(
    bridge: DirectBridge, path: str, value: int, timeout: float = 30.0
) -> CommandResult:
    """Set the render queue value on a material."""
    return await bridge.send_command_with_retry(
        command_type="material-operation",
        parameters={"operation": "set-render-queue", "materialPath": path, "renderQueue": value},
        timeout=timeout,
    )


async def material_copy_properties(
    bridge: DirectBridge, target_path: str, source_path: str, timeout: float = 30.0
) -> CommandResult:
    """Copy all properties from source material to target."""
    return await bridge.send_command_with_retry(
        command_type="material-operation",
        parameters={
            "operation": "copy-properties",
            "materialPath": target_path,
            "sourceMaterialPath": source_path,
        },
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
# Typer CLI wrappers
# ---------------------------------------------------------------------------

material_app = typer.Typer(name="material", help="Material management commands.")


def _print_material_operation(
    ctx: typer.Context,
    action: str,
    path: str,
    properties: dict[str, object] | None = None,
) -> None:
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(material_operation(state.bridge, action, path, properties))
    print_result(result, state.formatter)


@material_app.callback()
def material_cli() -> None:
    """Material management commands."""


@material_app.command("modify")
def modify_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Material asset path.")],
    properties: Annotated[
        str | None, typer.Option("--properties", help="JSON string of property overrides.")
    ] = None,
) -> None:
    """Modify material properties."""
    _print_material_operation(ctx, "modify", path, _parse_properties(properties))


@material_app.command("create")
def create_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Material asset path.")],
) -> None:
    """Create a material asset."""
    _print_material_operation(ctx, "create", path)


@material_app.command("duplicate")
def duplicate_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Material asset path.")],
) -> None:
    """Duplicate a material asset."""
    _print_material_operation(ctx, "duplicate", path)


@material_app.command("enable-keyword")
def enable_keyword_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Material asset path.")],
    keyword: Annotated[str, typer.Argument(help="Shader keyword to enable.")],
) -> None:
    """Enable a shader keyword on a material."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(material_enable_keyword(state.bridge, path, keyword))
    print_result(result, state.formatter)


@material_app.command("disable-keyword")
def disable_keyword_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Material asset path.")],
    keyword: Annotated[str, typer.Argument(help="Shader keyword to disable.")],
) -> None:
    """Disable a shader keyword on a material."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(material_disable_keyword(state.bridge, path, keyword))
    print_result(result, state.formatter)


@material_app.command("get-keywords")
def get_keywords_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Material asset path.")],
) -> None:
    """Get active shader keywords on a material."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(material_get_keywords(state.bridge, path))
    print_result(result, state.formatter)


@material_app.command("set-render-queue")
def set_render_queue_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Material asset path.")],
    value: Annotated[int, typer.Argument(help="Render queue value.")],
) -> None:
    """Set the render queue on a material."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(material_set_render_queue(state.bridge, path, value))
    print_result(result, state.formatter)


@material_app.command("copy-properties")
def copy_properties_cli(
    ctx: typer.Context,
    target_path: Annotated[str, typer.Argument(help="Target material path.")],
    source_path: Annotated[str, typer.Argument(help="Source material path.")],
) -> None:
    """Copy all properties from one material to another."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(material_copy_properties(state.bridge, target_path, source_path))
    print_result(result, state.formatter)

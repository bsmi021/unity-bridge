"""Shader inspection commands: list, info, errors, properties, find-by-property, keywords.

All operations are read-only. The ``shader-inspection`` command type is safe
for parallel batch execution.
"""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Valid operations
# ---------------------------------------------------------------------------

VALID_OPERATIONS = frozenset(
    {"list", "info", "errors", "properties", "find-by-property", "keywords"}
)

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def shader_list(
    bridge: DirectBridge,
    errors_only: bool = False,
    timeout: float = 15.0,
) -> CommandResult:
    """List all available shaders.

    Args:
        bridge: Active bridge connection.
        errors_only: Only return shaders with compilation errors.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {"operation": "list", "errorsOnly": errors_only}
    return await bridge.send_command_with_retry(
        command_type="shader-inspection",
        parameters=params,
        timeout=timeout,
    )


async def shader_info(
    bridge: DirectBridge,
    shader_name: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Get detailed info about a specific shader.

    Args:
        bridge: Active bridge connection.
        shader_name: Full shader name (e.g. ``Universal Render Pipeline/Lit``).
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="shader-inspection",
        parameters={"operation": "info", "shaderName": shader_name},
        timeout=timeout,
    )


async def shader_errors(
    bridge: DirectBridge,
    shader_name: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Get compilation errors and warnings for a shader.

    Args:
        bridge: Active bridge connection.
        shader_name: Full shader name.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="shader-inspection",
        parameters={"operation": "errors", "shaderName": shader_name},
        timeout=timeout,
    )


async def shader_properties(
    bridge: DirectBridge,
    shader_name: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Enumerate all properties of a shader.

    Args:
        bridge: Active bridge connection.
        shader_name: Full shader name.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="shader-inspection",
        parameters={"operation": "properties", "shaderName": shader_name},
        timeout=timeout,
    )


async def shader_find_by_property(
    bridge: DirectBridge,
    property_name: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Find all shaders that declare a given property.

    Args:
        bridge: Active bridge connection.
        property_name: Shader property name (e.g. ``_MainTex``).
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="shader-inspection",
        parameters={"operation": "find-by-property", "propertyName": property_name},
        timeout=timeout,
    )


async def shader_keywords(
    bridge: DirectBridge,
    shader_name: str,
    keyword_filter: str | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """List shader keywords (global, local, or both).

    Args:
        bridge: Active bridge connection.
        shader_name: Full shader name.
        keyword_filter: ``"global"``, ``"local"``, or ``None`` for both.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {"operation": "keywords", "shaderName": shader_name}
    if keyword_filter is not None:
        params["keywordFilter"] = keyword_filter
    return await bridge.send_command_with_retry(
        command_type="shader-inspection",
        parameters=params,
        timeout=timeout,
    )


async def shader_inspection_operation(
    bridge: DirectBridge,
    operation: str,
    shader_name: str | None = None,
    property_name: str | None = None,
    errors_only: bool = False,
    keyword_filter: str | None = None,
    timeout: float = 15.0,
) -> CommandResult:
    """Generic shader inspection operation (used by MCP dispatch).

    Args:
        bridge: Active bridge connection.
        operation: Operation to perform.
        shader_name: Full shader name (for info/errors/properties/keywords).
        property_name: Property name (for find-by-property).
        errors_only: Only return error shaders (for list).
        keyword_filter: ``"global"`` or ``"local"`` (for keywords).
        timeout: Timeout in seconds.

    Raises:
        ValueError: If *operation* is not recognised.
    """
    normalised = operation.lower().strip()
    if normalised not in VALID_OPERATIONS:
        raise ValueError(
            f"Invalid shader inspection operation '{operation}'. "
            f"Must be one of: {', '.join(sorted(VALID_OPERATIONS))}"
        )

    params: dict[str, object] = {"operation": normalised}
    if shader_name is not None:
        params["shaderName"] = shader_name
    if property_name is not None:
        params["propertyName"] = property_name
    if errors_only:
        params["errorsOnly"] = True
    if keyword_filter is not None:
        params["keywordFilter"] = keyword_filter

    return await bridge.send_command_with_retry(
        command_type="shader-inspection",
        parameters=params,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

shader_app = typer.Typer(
    name="shader",
    help="Shader inspection commands (read-only).",
)


@shader_app.command("list")
def shader_list_cli(
    ctx: typer.Context,
    errors_only: Annotated[
        bool,
        typer.Option("--errors-only", help="Only show shaders with compilation errors."),
    ] = False,
) -> None:
    """List all available shaders."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(shader_list(state.bridge, errors_only=errors_only))
    print_result(result, state.formatter)


@shader_app.command("info")
def shader_info_cli(
    ctx: typer.Context,
    name: Annotated[
        str,
        typer.Argument(help="Full shader name (e.g. 'Universal Render Pipeline/Lit')."),
    ],
) -> None:
    """Get detailed shader information."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(shader_info(state.bridge, name))
    print_result(result, state.formatter)


@shader_app.command("errors")
def shader_errors_cli(
    ctx: typer.Context,
    name: Annotated[
        str,
        typer.Argument(help="Full shader name."),
    ],
) -> None:
    """Get shader compilation errors and warnings."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(shader_errors(state.bridge, name))
    print_result(result, state.formatter)


@shader_app.command("properties")
def shader_properties_cli(
    ctx: typer.Context,
    name: Annotated[
        str,
        typer.Argument(help="Full shader name."),
    ],
) -> None:
    """Enumerate all shader properties."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(shader_properties(state.bridge, name))
    print_result(result, state.formatter)


@shader_app.command("find-by-property")
def shader_find_by_property_cli(
    ctx: typer.Context,
    property_name: Annotated[
        str,
        typer.Argument(help="Shader property name (e.g. '_MainTex')."),
    ],
) -> None:
    """Find shaders that declare a specific property."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(shader_find_by_property(state.bridge, property_name))
    print_result(result, state.formatter)


@shader_app.command("keywords")
def shader_keywords_cli(
    ctx: typer.Context,
    name: Annotated[
        str,
        typer.Argument(help="Full shader name."),
    ],
    filter_type: Annotated[
        str | None,
        typer.Option("--filter", help="'global' or 'local' to filter keyword type."),
    ] = None,
) -> None:
    """List shader keywords and variants."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(shader_keywords(state.bridge, name, keyword_filter=filter_type))
    print_result(result, state.formatter)

"""Import settings commands: get, set, reimport, bulk-set, template-save, template-apply.

Provides asset import settings inspection and modification through the
``import-settings-operation`` bridge command type.
"""

from __future__ import annotations

import asyncio
import re
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Valid operations
# ---------------------------------------------------------------------------

VALID_OPERATIONS = frozenset(
    {"get", "set", "reimport", "bulk-set", "template-save", "template-apply"}
)

_TEMPLATE_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def import_settings_get(
    bridge: DirectBridge,
    asset_path: str,
    timeout: float = 60.0,
) -> CommandResult:
    """Get current import settings for an asset.

    Args:
        bridge: Active bridge connection.
        asset_path: Asset path (e.g. ``Assets/Textures/Albedo.png``).
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="import-settings-operation",
        parameters={"operation": "get", "assetPath": asset_path},
        timeout=timeout,
    )


async def import_settings_set(
    bridge: DirectBridge,
    asset_path: str,
    settings: dict[str, str],
    timeout: float = 60.0,
) -> CommandResult:
    """Modify import settings and reimport an asset.

    Args:
        bridge: Active bridge connection.
        asset_path: Asset path.
        settings: Key-value pairs of settings to modify.
        timeout: Timeout in seconds.

    Raises:
        ValueError: If *settings* is empty.
    """
    if not settings:
        raise ValueError("At least one setting must be provided for 'set' operation")

    return await bridge.send_command_with_retry(
        command_type="import-settings-operation",
        parameters={
            "operation": "set",
            "assetPath": asset_path,
            "settings": settings,
        },
        timeout=timeout,
    )


async def import_settings_reimport(
    bridge: DirectBridge,
    asset_path: str,
    force: bool = False,
    timeout: float = 60.0,
) -> CommandResult:
    """Reimport an asset with current settings.

    Args:
        bridge: Active bridge connection.
        asset_path: Asset path.
        force: Force reimport even if unchanged.
        timeout: Timeout in seconds.
    """
    params: dict[str, object] = {
        "operation": "reimport",
        "assetPath": asset_path,
    }
    if force:
        params["force"] = True
    return await bridge.send_command_with_retry(
        command_type="import-settings-operation",
        parameters=params,
        timeout=timeout,
    )


async def import_settings_bulk_set(
    bridge: DirectBridge,
    folder_path: str,
    settings: dict[str, str],
    filter_pattern: str | None = None,
    timeout: float = 60.0,
) -> CommandResult:
    """Apply settings to all matching assets in a folder.

    Args:
        bridge: Active bridge connection.
        folder_path: Folder path to search.
        settings: Key-value pairs of settings to modify.
        filter_pattern: Glob filter pattern (e.g. ``*.png``).
        timeout: Timeout in seconds.

    Raises:
        ValueError: If *settings* is empty.
    """
    if not settings:
        raise ValueError("At least one setting must be provided for 'bulk-set' operation")

    params: dict[str, object] = {
        "operation": "bulk-set",
        "folderPath": folder_path,
        "settings": settings,
    }
    if filter_pattern is not None:
        params["filter"] = filter_pattern
    return await bridge.send_command_with_retry(
        command_type="import-settings-operation",
        parameters=params,
        timeout=timeout,
    )


async def import_settings_template_save(
    bridge: DirectBridge,
    template_name: str,
    asset_path: str,
    timeout: float = 60.0,
) -> CommandResult:
    """Save current import settings of an asset as a named template.

    Args:
        bridge: Active bridge connection.
        template_name: Template name (alphanumeric, hyphens, underscores, max 64).
        asset_path: Source asset path.
        timeout: Timeout in seconds.

    Raises:
        ValueError: If *template_name* is invalid.
    """
    _validate_template_name(template_name)
    return await bridge.send_command_with_retry(
        command_type="import-settings-operation",
        parameters={
            "operation": "template-save",
            "templateName": template_name,
            "assetPath": asset_path,
        },
        timeout=timeout,
    )


async def import_settings_template_apply(
    bridge: DirectBridge,
    template_name: str,
    asset_path: str,
    timeout: float = 60.0,
) -> CommandResult:
    """Apply a saved template to a target asset.

    Args:
        bridge: Active bridge connection.
        template_name: Template name.
        asset_path: Target asset path.
        timeout: Timeout in seconds.
    """
    return await bridge.send_command_with_retry(
        command_type="import-settings-operation",
        parameters={
            "operation": "template-apply",
            "templateName": template_name,
            "assetPath": asset_path,
        },
        timeout=timeout,
    )


async def import_settings_operation(
    bridge: DirectBridge,
    operation: str,
    asset_path: str | None = None,
    settings: dict[str, str] | None = None,
    force: bool = False,
    template_name: str | None = None,
    folder_path: str | None = None,
    filter_pattern: str | None = None,
    timeout: float = 60.0,
) -> CommandResult:
    """Generic import settings operation (used by MCP dispatch).

    Args:
        bridge: Active bridge connection.
        operation: Operation to perform.
        asset_path: Asset path for get/set/reimport/template operations.
        settings: Settings dict for set/bulk-set.
        force: Force reimport flag.
        template_name: Template name for template operations.
        folder_path: Folder path for bulk-set.
        filter_pattern: Glob filter for bulk-set.
        timeout: Timeout in seconds.

    Raises:
        ValueError: If *operation* is not recognised.
    """
    normalised = operation.lower().strip()
    if normalised not in VALID_OPERATIONS:
        raise ValueError(
            f"Invalid import settings operation '{operation}'. "
            f"Must be one of: {', '.join(sorted(VALID_OPERATIONS))}"
        )

    params: dict[str, object] = {"operation": normalised}
    if asset_path is not None:
        params["assetPath"] = asset_path
    if settings is not None:
        params["settings"] = settings
    if force:
        params["force"] = True
    if template_name is not None:
        params["templateName"] = template_name
    if folder_path is not None:
        params["folderPath"] = folder_path
    if filter_pattern is not None:
        params["filter"] = filter_pattern

    return await bridge.send_command_with_retry(
        command_type="import-settings-operation",
        parameters=params,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_template_name(name: str) -> None:
    """Validate template name format."""
    if not name or len(name) > 64 or not _TEMPLATE_NAME_RE.match(name):
        raise ValueError(
            f"Invalid template name '{name}'. "
            "Must be alphanumeric with hyphens/underscores, max 64 characters."
        )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

import_settings_app = typer.Typer(
    name="import-settings",
    help="Asset import settings commands.",
)


@import_settings_app.command("get")
def import_settings_get_cli(
    ctx: typer.Context,
    path: Annotated[
        str,
        typer.Argument(help="Asset path (e.g. Assets/Textures/Albedo.png)."),
    ],
) -> None:
    """Get current import settings for an asset."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(import_settings_get(state.bridge, path))
    print_result(result, state.formatter)


@import_settings_app.command("set")
def import_settings_set_cli(
    ctx: typer.Context,
    path: Annotated[
        str,
        typer.Argument(help="Asset path."),
    ],
    setting: Annotated[
        list[str],
        typer.Option("--setting", "-s", help="Setting as key:value (repeatable)."),
    ] = [],
) -> None:
    """Modify import settings and reimport."""
    from unity_bridge.core.output import print_result

    settings_dict = {}
    for s in setting:
        if ":" not in s:
            raise typer.BadParameter(f"Setting must be key:value format, got: {s}")
        key, value = s.split(":", 1)
        settings_dict[key.strip()] = value.strip()

    state = ctx.obj
    result = asyncio.run(import_settings_set(state.bridge, path, settings_dict))
    print_result(result, state.formatter)


@import_settings_app.command("reimport")
def import_settings_reimport_cli(
    ctx: typer.Context,
    path: Annotated[
        str,
        typer.Argument(help="Asset path."),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", help="Force reimport even if unchanged."),
    ] = False,
) -> None:
    """Reimport an asset with current settings."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(import_settings_reimport(state.bridge, path, force=force))
    print_result(result, state.formatter)


@import_settings_app.command("bulk-set")
def import_settings_bulk_set_cli(
    ctx: typer.Context,
    folder: Annotated[
        str,
        typer.Argument(help="Folder path."),
    ],
    setting: Annotated[
        list[str],
        typer.Option("--setting", "-s", help="Setting as key:value (repeatable)."),
    ] = [],
    filter_pattern: Annotated[
        str | None,
        typer.Option("--filter", help="Glob filter (e.g. '*.png')."),
    ] = None,
) -> None:
    """Bulk-modify import settings for all matching assets."""
    from unity_bridge.core.output import print_result

    settings_dict = {}
    for s in setting:
        if ":" not in s:
            raise typer.BadParameter(f"Setting must be key:value format, got: {s}")
        key, value = s.split(":", 1)
        settings_dict[key.strip()] = value.strip()

    state = ctx.obj
    result = asyncio.run(
        import_settings_bulk_set(state.bridge, folder, settings_dict, filter_pattern)
    )
    print_result(result, state.formatter)


@import_settings_app.command("template-save")
def import_settings_template_save_cli(
    ctx: typer.Context,
    name: Annotated[
        str,
        typer.Argument(help="Template name."),
    ],
    path: Annotated[
        str,
        typer.Argument(help="Source asset path."),
    ],
) -> None:
    """Save current import settings as a named template."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(import_settings_template_save(state.bridge, name, path))
    print_result(result, state.formatter)


@import_settings_app.command("template-apply")
def import_settings_template_apply_cli(
    ctx: typer.Context,
    name: Annotated[
        str,
        typer.Argument(help="Template name."),
    ],
    path: Annotated[
        str,
        typer.Argument(help="Target asset path."),
    ],
) -> None:
    """Apply a saved template to an asset."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(import_settings_template_apply(state.bridge, name, path))
    print_result(result, state.formatter)

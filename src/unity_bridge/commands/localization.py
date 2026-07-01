"""Localization commands: locales, string tables, entries, CSV/XLIFF import-export."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async functions (CLI + MCP)
# ---------------------------------------------------------------------------


async def list_locales(bridge: DirectBridge, timeout: float = 10.0) -> CommandResult:
    """List registered locales."""
    return await bridge.send_command_with_retry(
        command_type="localization",
        parameters={"operation": "list-locales"},
        timeout=timeout,
    )


async def add_locale(
    bridge: DirectBridge, locale_code: str, timeout: float = 15.0
) -> CommandResult:
    """Add a locale by code (e.g. "en", "fr")."""
    return await bridge.send_command_with_retry(
        command_type="localization",
        parameters={"operation": "add-locale", "localeCode": locale_code},
        timeout=timeout,
    )


async def remove_locale(
    bridge: DirectBridge, locale_code: str, timeout: float = 15.0
) -> CommandResult:
    """Remove a locale by code."""
    return await bridge.send_command_with_retry(
        command_type="localization",
        parameters={"operation": "remove-locale", "localeCode": locale_code},
        timeout=timeout,
    )


async def get_selected_locale(bridge: DirectBridge, timeout: float = 10.0) -> CommandResult:
    """Get the currently selected locale."""
    return await bridge.send_command_with_retry(
        command_type="localization",
        parameters={"operation": "get-selected-locale"},
        timeout=timeout,
    )


async def set_selected_locale(
    bridge: DirectBridge, locale_code: str, timeout: float = 15.0
) -> CommandResult:
    """Set the currently selected locale by code."""
    return await bridge.send_command_with_retry(
        command_type="localization",
        parameters={"operation": "set-selected-locale", "localeCode": locale_code},
        timeout=timeout,
    )


async def create_string_table_collection(
    bridge: DirectBridge, table_collection_name: str, timeout: float = 30.0
) -> CommandResult:
    """Create a new string table collection."""
    return await bridge.send_command_with_retry(
        command_type="localization",
        parameters={
            "operation": "create-string-table-collection",
            "tableCollectionName": table_collection_name,
        },
        timeout=timeout,
    )


async def get_string_table_collection(
    bridge: DirectBridge, table_collection_name: str, timeout: float = 10.0
) -> CommandResult:
    """Get a string table collection by name."""
    return await bridge.send_command_with_retry(
        command_type="localization",
        parameters={
            "operation": "get-string-table-collection",
            "tableCollectionName": table_collection_name,
        },
        timeout=timeout,
    )


async def add_entry(
    bridge: DirectBridge,
    table_collection_name: str,
    key: str,
    value: str,
    timeout: float = 15.0,
) -> CommandResult:
    """Add a key/value entry to a string table collection."""
    return await bridge.send_command_with_retry(
        command_type="localization",
        parameters={
            "operation": "add-entry",
            "tableCollectionName": table_collection_name,
            "key": key,
            "value": value,
        },
        timeout=timeout,
    )


async def export_csv(
    bridge: DirectBridge,
    table_collection_name: str,
    file_path: str,
    timeout: float = 60.0,
) -> CommandResult:
    """Export a string table collection to CSV."""
    return await bridge.send_command_with_retry(
        command_type="localization",
        parameters={
            "operation": "export-csv",
            "tableCollectionName": table_collection_name,
            "filePath": file_path,
        },
        timeout=timeout,
    )


async def import_csv(
    bridge: DirectBridge,
    table_collection_name: str,
    file_path: str,
    timeout: float = 60.0,
) -> CommandResult:
    """Import a CSV file into a string table collection."""
    return await bridge.send_command_with_retry(
        command_type="localization",
        parameters={
            "operation": "import-csv",
            "tableCollectionName": table_collection_name,
            "filePath": file_path,
        },
        timeout=timeout,
    )


async def export_xliff(
    bridge: DirectBridge,
    table_collection_name: str,
    file_path: str,
    timeout: float = 60.0,
) -> CommandResult:
    """Export a string table collection to XLIFF."""
    return await bridge.send_command_with_retry(
        command_type="localization",
        parameters={
            "operation": "export-xliff",
            "tableCollectionName": table_collection_name,
            "filePath": file_path,
        },
        timeout=timeout,
    )


async def import_xliff(
    bridge: DirectBridge,
    table_collection_name: str,
    file_path: str,
    timeout: float = 60.0,
) -> CommandResult:
    """Import an XLIFF file into a string table collection."""
    return await bridge.send_command_with_retry(
        command_type="localization",
        parameters={
            "operation": "import-xliff",
            "tableCollectionName": table_collection_name,
            "filePath": file_path,
        },
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI wrappers
# ---------------------------------------------------------------------------

localization_app = typer.Typer(name="localization", help="Localization package commands.")


@localization_app.command("list-locales")
def list_locales_cli(ctx: typer.Context) -> None:
    """List registered locales."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    print_result(asyncio.run(list_locales(state.bridge)), state.formatter)


@localization_app.command("add-locale")
def add_locale_cli(
    ctx: typer.Context,
    locale_code: Annotated[str, typer.Argument(help="Locale code, e.g. fr.")],
) -> None:
    """Add a locale by code."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    print_result(asyncio.run(add_locale(state.bridge, locale_code)), state.formatter)


@localization_app.command("remove-locale")
def remove_locale_cli(
    ctx: typer.Context,
    locale_code: Annotated[str, typer.Argument(help="Locale code, e.g. fr.")],
) -> None:
    """Remove a locale by code."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    print_result(asyncio.run(remove_locale(state.bridge, locale_code)), state.formatter)


@localization_app.command("get-selected-locale")
def get_selected_locale_cli(ctx: typer.Context) -> None:
    """Get the currently selected locale."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    print_result(asyncio.run(get_selected_locale(state.bridge)), state.formatter)


@localization_app.command("set-selected-locale")
def set_selected_locale_cli(
    ctx: typer.Context,
    locale_code: Annotated[str, typer.Argument(help="Locale code, e.g. de.")],
) -> None:
    """Set the currently selected locale by code."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    print_result(asyncio.run(set_selected_locale(state.bridge, locale_code)), state.formatter)


@localization_app.command("create-string-table-collection")
def create_string_table_collection_cli(
    ctx: typer.Context,
    table_collection_name: Annotated[str, typer.Argument(help="Collection name.")],
) -> None:
    """Create a new string table collection."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(create_string_table_collection(state.bridge, table_collection_name))
    print_result(result, state.formatter)


@localization_app.command("get-string-table-collection")
def get_string_table_collection_cli(
    ctx: typer.Context,
    table_collection_name: Annotated[str, typer.Argument(help="Collection name.")],
) -> None:
    """Get a string table collection by name."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(get_string_table_collection(state.bridge, table_collection_name))
    print_result(result, state.formatter)


@localization_app.command("add-entry")
def add_entry_cli(
    ctx: typer.Context,
    table_collection_name: Annotated[str, typer.Argument(help="Collection name.")],
    key: Annotated[str, typer.Argument(help="Entry key.")],
    value: Annotated[str, typer.Argument(help="Entry value.")],
) -> None:
    """Add a key/value entry to a string table collection."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(add_entry(state.bridge, table_collection_name, key, value))
    print_result(result, state.formatter)


@localization_app.command("export-csv")
def export_csv_cli(
    ctx: typer.Context,
    table_collection_name: Annotated[str, typer.Argument(help="Collection name.")],
    file_path: Annotated[str, typer.Argument(help="Destination CSV path.")],
) -> None:
    """Export a string table collection to CSV."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(export_csv(state.bridge, table_collection_name, file_path))
    print_result(result, state.formatter)


@localization_app.command("import-csv")
def import_csv_cli(
    ctx: typer.Context,
    table_collection_name: Annotated[str, typer.Argument(help="Collection name.")],
    file_path: Annotated[str, typer.Argument(help="Source CSV path.")],
) -> None:
    """Import a CSV file into a string table collection."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(import_csv(state.bridge, table_collection_name, file_path))
    print_result(result, state.formatter)


@localization_app.command("export-xliff")
def export_xliff_cli(
    ctx: typer.Context,
    table_collection_name: Annotated[str, typer.Argument(help="Collection name.")],
    file_path: Annotated[str, typer.Argument(help="Destination XLIFF path.")],
) -> None:
    """Export a string table collection to XLIFF."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(export_xliff(state.bridge, table_collection_name, file_path))
    print_result(result, state.formatter)


@localization_app.command("import-xliff")
def import_xliff_cli(
    ctx: typer.Context,
    table_collection_name: Annotated[str, typer.Argument(help="Collection name.")],
    file_path: Annotated[str, typer.Argument(help="Source XLIFF path.")],
) -> None:
    """Import an XLIFF file into a string table collection."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(import_xliff(state.bridge, table_collection_name, file_path))
    print_result(result, state.formatter)

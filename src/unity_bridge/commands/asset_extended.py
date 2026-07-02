"""Asset extended commands: create, delete, copy, move, deps, guid, folders, export/import."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Valid operations
# ---------------------------------------------------------------------------

VALID_OPERATIONS = frozenset(
    {
        "create",
        "delete",
        "copy",
        "move",
        "deps",
        "guid",
        "hash",
        "folder-create",
        "folder-list",
        "export",
        "import-package",
        "import-model",
        "reserialize",
    }
)

MUTATING_OPERATIONS = frozenset(
    {
        "create",
        "delete",
        "copy",
        "move",
        "folder-create",
        "export",
        "import-package",
        "import-model",
        "reserialize",
    }
)

# ---------------------------------------------------------------------------
# Core async function (CLI + MCP)
# ---------------------------------------------------------------------------


async def asset_extended_operation(
    bridge: DirectBridge,
    action: str,
    *,
    asset_path: str | None = None,
    source_path: str | None = None,
    destination_path: str | None = None,
    asset_type: str | None = None,
    use_trash: bool = False,
    recursive: bool = True,
    input_value: str | None = None,
    folder_path: str | None = None,
    asset_paths: list[str] | None = None,
    output_path: str | None = None,
    include_dependencies: bool = True,
    interactive: bool = False,
    package_path: str | None = None,
    reserialize_mode: str | None = None,
    timeout: float = 60.0,
) -> CommandResult:
    """Perform an extended asset database operation.

    Args:
        bridge: Active bridge connection.
        action: Operation — create, delete, copy, move, deps, guid,
                folder-create, folder-list, export, import-package,
                import-model, reserialize, hash.
        asset_path: Primary asset path for create/delete/deps.
        source_path: Source path for copy/move/import-model.
        destination_path: Destination path for copy/move/import-model.
        asset_type: Asset type for create (e.g. ScriptableObject, Material).
        use_trash: Move to trash instead of permanent delete.
        recursive: Include transitive dependencies for deps.
        input_value: Path or GUID for guid operation.
        folder_path: Folder path for folder-create/folder-list.
        asset_paths: Multiple asset paths for export.
        output_path: Output file path for export.
        include_dependencies: Include dependencies in export.
        interactive: Show import dialog for import-package.
        package_path: Path to .unitypackage for import-package.
        reserialize_mode: Mode for reserialize (assets, metadata, both).
        timeout: Command timeout in seconds.

    Raises:
        ValueError: If *action* is not a recognised operation.
    """
    normalised = action.lower().strip()
    if normalised not in VALID_OPERATIONS:
        raise ValueError(
            f"Invalid asset extended action '{action}'. "
            f"Must be one of: {', '.join(sorted(VALID_OPERATIONS))}"
        )

    params: dict[str, object] = {"operation": normalised}

    if asset_path is not None:
        params["assetPath"] = asset_path
    if source_path is not None:
        params["sourcePath"] = source_path
    if destination_path is not None:
        params["destinationPath"] = destination_path
    if asset_type is not None:
        params["assetType"] = asset_type
    if use_trash:
        params["useTrash"] = True
    if not recursive:
        params["recursive"] = False
    if input_value is not None:
        params["input"] = input_value
    if folder_path is not None:
        params["folderPath"] = folder_path
    if asset_paths is not None:
        params["assetPaths"] = asset_paths
    if output_path is not None:
        params["outputPath"] = output_path
    if not include_dependencies:
        params["includeDependencies"] = False
    if interactive:
        params["interactive"] = True
    if package_path is not None:
        params["packagePath"] = package_path
    if reserialize_mode is not None:
        params["reserializeMode"] = reserialize_mode

    return await bridge.send_command_with_retry(
        command_type="asset-extended-operation",
        parameters=params,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI
# ---------------------------------------------------------------------------

asset_ext_app = typer.Typer(
    name="asset-ext",
    help="Extended asset database operations (create, delete, copy, move, etc.).",
)


@asset_ext_app.command("create")
def asset_create_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Asset path (e.g. Assets/Data/Config.asset)")],
    asset_type: Annotated[
        str, typer.Option("--type", "-t", help="Asset type (ScriptableObject, Material, etc.)")
    ],
) -> None:
    """Create a new asset at the specified path."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        asset_extended_operation(state.bridge, "create", asset_path=path, asset_type=asset_type)
    )
    print_result(result, state.formatter)


@asset_ext_app.command("delete")
def asset_delete_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Asset path to delete")],
    trash: Annotated[
        bool, typer.Option("--trash", help="Move to trash instead of permanent delete.")
    ] = False,
) -> None:
    """Delete an asset (permanently or to trash)."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        asset_extended_operation(state.bridge, "delete", asset_path=path, use_trash=trash)
    )
    print_result(result, state.formatter)


@asset_ext_app.command("copy")
def asset_copy_cli(
    ctx: typer.Context,
    source: Annotated[str, typer.Argument(help="Source asset path")],
    dest: Annotated[str, typer.Argument(help="Destination asset path")],
) -> None:
    """Copy an asset to a new path."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        asset_extended_operation(state.bridge, "copy", source_path=source, destination_path=dest)
    )
    print_result(result, state.formatter)


@asset_ext_app.command("move")
def asset_move_cli(
    ctx: typer.Context,
    source: Annotated[str, typer.Argument(help="Source asset path")],
    dest: Annotated[str, typer.Argument(help="Destination asset path")],
) -> None:
    """Move or rename an asset."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        asset_extended_operation(state.bridge, "move", source_path=source, destination_path=dest)
    )
    print_result(result, state.formatter)


@asset_ext_app.command("deps")
def asset_deps_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Asset path to check dependencies")],
    recursive: Annotated[
        bool, typer.Option("--recursive/--no-recursive", help="Include transitive dependencies.")
    ] = True,
) -> None:
    """List dependencies of an asset."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        asset_extended_operation(state.bridge, "deps", asset_path=path, recursive=recursive)
    )
    print_result(result, state.formatter)


@asset_ext_app.command("guid")
def asset_guid_cli(
    ctx: typer.Context,
    input_val: Annotated[str, typer.Argument(help="Asset path or GUID to convert")],
) -> None:
    """Convert between asset path and GUID."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(asset_extended_operation(state.bridge, "guid", input_value=input_val))
    print_result(result, state.formatter)


@asset_ext_app.command("hash")
def asset_hash_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Asset path to hash.")],
) -> None:
    """Compute a SHA256 hash for an asset file."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(asset_extended_operation(state.bridge, "hash", asset_path=path))
    print_result(result, state.formatter)


@asset_ext_app.command("folder-create")
def asset_folder_create_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Folder path to create (e.g. Assets/Data/Configs)")],
) -> None:
    """Create a folder in the Unity project."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(asset_extended_operation(state.bridge, "folder-create", folder_path=path))
    print_result(result, state.formatter)


@asset_ext_app.command("folder-list")
def asset_folder_list_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Folder path to list subfolders")],
) -> None:
    """List subfolders of a folder."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(asset_extended_operation(state.bridge, "folder-list", folder_path=path))
    print_result(result, state.formatter)


@asset_ext_app.command("export")
def asset_export_cli(
    ctx: typer.Context,
    output: Annotated[str, typer.Option("--output", "-o", help="Output .unitypackage path")],
    paths: Annotated[list[str], typer.Argument(help="Asset paths to export")] = None,
    include_deps: Annotated[
        bool, typer.Option("--include-deps/--no-deps", help="Include dependencies.")
    ] = True,
) -> None:
    """Export assets as a .unitypackage file."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        asset_extended_operation(
            state.bridge,
            "export",
            asset_paths=paths or [],
            output_path=output,
            include_dependencies=include_deps,
        )
    )
    print_result(result, state.formatter)


@asset_ext_app.command("import-package")
def asset_import_package_cli(
    ctx: typer.Context,
    package: Annotated[str, typer.Argument(help="Path to .unitypackage file")],
    interactive: Annotated[bool, typer.Option("--interactive", help="Show import dialog.")] = False,
) -> None:
    """Import a .unitypackage file."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        asset_extended_operation(
            state.bridge,
            "import-package",
            package_path=package,
            interactive=interactive,
        )
    )
    print_result(result, state.formatter)


@asset_ext_app.command("import-model")
def asset_import_model_cli(
    ctx: typer.Context,
    source: Annotated[str, typer.Argument(help="External model file path.")],
    dest: Annotated[str, typer.Argument(help="Destination Assets/ path.")],
) -> None:
    """Copy an external model file into Assets/ and import it."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        asset_extended_operation(
            state.bridge,
            "import-model",
            source_path=source,
            destination_path=dest,
        )
    )
    print_result(result, state.formatter)

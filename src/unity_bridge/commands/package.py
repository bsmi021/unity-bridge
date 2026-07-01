"""Package Manager commands for Unity Package Manager operations."""

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
        "list",
        "search",
        "search-all",
        "add",
        "batch",
        "remove",
        "info",
        "embed",
        "resolve",
        "pack",
        "clear-cache",
    }
)

# ---------------------------------------------------------------------------
# Core async function (CLI + MCP)
# ---------------------------------------------------------------------------


async def package_operation(
    bridge: DirectBridge,
    action: str,
    *,
    identifier: str | None = None,
    package_name: str | None = None,
    query: str | None = None,
    source: str | None = None,
    packages_to_add: list[str] | None = None,
    packages_to_remove: list[str] | None = None,
    package_folder: str | None = None,
    target_folder: str | None = None,
    confirm_clear_cache: bool = False,
    offline_mode: bool = False,
    include_indirect: bool = False,
    timeout: float = 60.0,
) -> CommandResult:
    """Perform a Unity Package Manager operation.

    Args:
        bridge: Active bridge connection.
        action: Package operation to perform.
        identifier: Package identifier for add (name@version or git URL).
        package_name: Package name for remove/info/embed.
        query: Search query for search operation.
        source: Filter by source type for list (registry, git, embedded, local).
        packages_to_add: Package identifiers for batch add/remove.
        packages_to_remove: Package names for batch add/remove.
        package_folder: Folder containing package.json for pack.
        target_folder: Folder where pack writes the .tgz file.
        confirm_clear_cache: Required confirmation flag for clear-cache.
        offline_mode: Use cached data only for list.
        include_indirect: Include transitive dependencies for list.
        timeout: Command timeout in seconds.

    Raises:
        ValueError: If *action* is not a recognised operation.
    """
    normalised = action.lower().strip()
    if normalised not in VALID_OPERATIONS:
        raise ValueError(
            f"Invalid package action '{action}'. "
            f"Must be one of: {', '.join(sorted(VALID_OPERATIONS))}"
        )

    params: dict[str, object] = {"operation": normalised}

    if identifier is not None:
        params["identifier"] = identifier
    if package_name is not None:
        params["packageName"] = package_name
    if query is not None:
        params["query"] = query
    if source is not None:
        params["source"] = source
    if packages_to_add is not None:
        params["packagesToAdd"] = packages_to_add
    if packages_to_remove is not None:
        params["packagesToRemove"] = packages_to_remove
    if package_folder is not None:
        params["packageFolder"] = package_folder
    if target_folder is not None:
        params["targetFolder"] = target_folder
    if confirm_clear_cache:
        params["confirmClearCache"] = True
    if offline_mode:
        params["offlineMode"] = True
    if include_indirect:
        params["includeIndirectDependencies"] = True

    return await bridge.send_command_with_retry(
        command_type="package-operation",
        parameters=params,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Typer CLI
# ---------------------------------------------------------------------------

package_app = typer.Typer(
    name="package",
    help="Unity Package Manager operations.",
)


@package_app.command("list")
def package_list_cli(
    ctx: typer.Context,
    offline: Annotated[bool, typer.Option("--offline", help="Use cached data only.")] = False,
    include_indirect: Annotated[
        bool, typer.Option("--include-indirect", help="Include transitive dependencies.")
    ] = False,
    source: Annotated[
        str | None,
        typer.Option("--source", "-s", help="Filter by source (registry, git, embedded, local)."),
    ] = None,
) -> None:
    """List installed packages."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        package_operation(
            state.bridge,
            "list",
            offline_mode=offline,
            include_indirect=include_indirect,
            source=source,
        )
    )
    print_result(result, state.formatter)


@package_app.command("search")
def package_search_cli(
    ctx: typer.Context,
    query: Annotated[str, typer.Argument(help="Package ID or name to search for")],
    all_packages: Annotated[
        bool, typer.Option("--all", help="List all available packages instead of searching.")
    ] = False,
) -> None:
    """Search for packages by ID/name."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    if all_packages:
        result = asyncio.run(package_operation(state.bridge, "search-all"))
    else:
        result = asyncio.run(package_operation(state.bridge, "search", query=query))
    print_result(result, state.formatter)


@package_app.command("add")
def package_add_cli(
    ctx: typer.Context,
    identifier: Annotated[str, typer.Argument(help="Package identifier (name@version or git URL)")],
) -> None:
    """Add a package by identifier."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(package_operation(state.bridge, "add", identifier=identifier))
    print_result(result, state.formatter)


@package_app.command("batch")
def package_batch_cli(
    ctx: typer.Context,
    add: Annotated[
        list[str] | None,
        typer.Option("--add", help="Package identifier to add; repeat for multiple."),
    ] = None,
    remove: Annotated[
        list[str] | None,
        typer.Option("--remove", help="Package name to remove; repeat for multiple."),
    ] = None,
) -> None:
    """Add and remove packages in one dependency resolution pass."""
    from unity_bridge.core.output import print_result

    if not add and not remove:
        raise typer.BadParameter("Pass at least one --add or --remove value.")

    state = ctx.obj
    result = asyncio.run(
        package_operation(
            state.bridge,
            "batch",
            packages_to_add=add,
            packages_to_remove=remove,
        )
    )
    print_result(result, state.formatter)


@package_app.command("remove")
def package_remove_cli(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Package name to remove")],
) -> None:
    """Remove a package."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(package_operation(state.bridge, "remove", package_name=name))
    print_result(result, state.formatter)


@package_app.command("info")
def package_info_cli(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Package name to get info for")],
) -> None:
    """Get detailed package information."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(package_operation(state.bridge, "info", package_name=name))
    print_result(result, state.formatter)


@package_app.command("embed")
def package_embed_cli(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Package name to embed")],
) -> None:
    """Embed a package into the Packages/ folder."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(package_operation(state.bridge, "embed", package_name=name))
    print_result(result, state.formatter)


@package_app.command("pack")
def package_pack_cli(
    ctx: typer.Context,
    package_folder: Annotated[str, typer.Argument(help="Folder containing package.json")],
    target_folder: Annotated[str, typer.Argument(help="Folder to write the .tgz file into")],
) -> None:
    """Pack a UPM package folder into a .tgz tarball."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        package_operation(
            state.bridge,
            "pack",
            package_folder=package_folder,
            target_folder=target_folder,
        )
    )
    print_result(result, state.formatter)


@package_app.command("clear-cache")
def package_clear_cache_cli(
    ctx: typer.Context,
    yes: Annotated[
        bool,
        typer.Option("--yes", help="Confirm clearing the global Unity package cache."),
    ] = False,
) -> None:
    """Clear Unity's global Package Manager cache."""
    from unity_bridge.core.output import print_result

    if not yes:
        raise typer.BadParameter("Pass --yes to clear Unity's global package cache.")

    state = ctx.obj
    result = asyncio.run(
        package_operation(state.bridge, "clear-cache", confirm_clear_cache=True)
    )
    print_result(result, state.formatter)


@package_app.command("resolve")
def package_resolve_cli(
    ctx: typer.Context,
) -> None:
    """Trigger package resolution."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(package_operation(state.bridge, "resolve"))
    print_result(result, state.formatter)

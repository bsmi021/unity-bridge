"""Package Manager commands: list, search, add, remove, info, embed, resolve."""

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
        "remove",
        "info",
        "embed",
        "resolve",
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
    offline_mode: bool = False,
    include_indirect: bool = False,
    timeout: float = 60.0,
) -> CommandResult:
    """Perform a Unity Package Manager operation.

    Args:
        bridge: Active bridge connection.
        action: Operation — list, search, search-all, add, remove, info, embed, resolve.
        identifier: Package identifier for add (name@version or git URL).
        package_name: Package name for remove/info/embed.
        query: Search query for search operation.
        source: Filter by source type for list (registry, git, embedded, local).
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


@package_app.command("resolve")
def package_resolve_cli(
    ctx: typer.Context,
) -> None:
    """Trigger package resolution."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(package_operation(state.bridge, "resolve"))
    print_result(result, state.formatter)

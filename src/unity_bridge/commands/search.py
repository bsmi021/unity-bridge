"""Unity Search (Quick Search) queries.

Exposes ``UnityEditor.Search.SearchService.Request`` — the Editor's
general-purpose query engine spanning assets, scenes, menus, packages,
and settings. One handler subsumes a large class of "find X" workflows.
"""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge


async def search_query(
    bridge: DirectBridge,
    query: str,
    max_results: int = 100,
    timeout: float = 30.0,
) -> CommandResult:
    """Run a Quick Search query and return ranked results."""
    return await bridge.send_command_with_retry(
        command_type="search-query",
        parameters={
            "operation": "query",
            "query": query,
            "maxResults": max_results,
        },
        timeout=timeout,
    )


async def search_providers(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """List registered Search providers (asset, scene, menu, etc.)."""
    return await bridge.send_command_with_retry(
        command_type="search-query",
        parameters={"operation": "providers"},
        timeout=timeout,
    )


search_app = typer.Typer(
    name="search",
    help="Unity Search (Quick Search) queries.",
)


@search_app.command("query")
def query_cli(
    ctx: typer.Context,
    query: Annotated[str, typer.Argument(help="Quick Search query string.")],
    max_results: Annotated[
        int,
        typer.Option("--max", help="Maximum results to return."),
    ] = 100,
) -> None:
    """Run a Quick Search query."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(search_query(state.bridge, query, max_results))
    print_result(result, state.formatter)


@search_app.command("providers")
def providers_cli(ctx: typer.Context) -> None:
    """List available Search providers."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(search_providers(state.bridge))
    print_result(result, state.formatter)

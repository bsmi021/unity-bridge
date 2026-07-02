"""Safe MonoScript text edits with optional SHA256 preconditions."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge


async def script_edit_range(
    bridge: DirectBridge,
    asset_path: str,
    *,
    start_line: int,
    end_line: int,
    replacement: str,
    if_match: str | None = None,
    timeout: float = 60.0,
) -> CommandResult:
    """Replace a one-based inclusive line range in a C# asset."""
    params: dict[str, object] = {
        "operation": "range",
        "assetPath": asset_path,
        "startLine": start_line,
        "endLine": end_line,
        "replacement": replacement,
    }
    if if_match is not None:
        params["ifMatch"] = if_match
    return await bridge.send_command_with_retry(
        command_type="script-edit",
        parameters=params,
        timeout=timeout,
    )


async def script_edit_anchor(
    bridge: DirectBridge,
    asset_path: str,
    *,
    anchor: str,
    replacement: str,
    occurrence: int = 1,
    if_match: str | None = None,
    timeout: float = 60.0,
) -> CommandResult:
    """Replace the Nth exact anchor occurrence in a C# asset."""
    params: dict[str, object] = {
        "operation": "anchor",
        "assetPath": asset_path,
        "anchor": anchor,
        "replacement": replacement,
        "occurrence": occurrence,
    }
    if if_match is not None:
        params["ifMatch"] = if_match
    return await bridge.send_command_with_retry(
        command_type="script-edit",
        parameters=params,
        timeout=timeout,
    )


script_edit_app = typer.Typer(name="script-edit", help="Safe MonoScript text edits.")


@script_edit_app.command("range")
def script_edit_range_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Asset path to the .cs script.")],
    start_line: Annotated[int, typer.Option("--start-line", help="First line to replace.")],
    end_line: Annotated[int, typer.Option("--end-line", help="Last line to replace.")],
    replacement: Annotated[str, typer.Option("--replacement", "-r", help="Replacement text.")],
    if_match: Annotated[
        str | None,
        typer.Option("--if-match", help="Expected current SHA256 before writing."),
    ] = None,
    timeout: Annotated[float, typer.Option("--timeout", help="Timeout in seconds.")] = 60.0,
) -> None:
    """Replace a one-based inclusive line range."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        script_edit_range(
            state.bridge,
            path,
            start_line=start_line,
            end_line=end_line,
            replacement=replacement,
            if_match=if_match,
            timeout=timeout,
        )
    )
    print_result(result, state.formatter)


@script_edit_app.command("anchor")
def script_edit_anchor_cli(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Asset path to the .cs script.")],
    anchor: Annotated[str, typer.Option("--anchor", "-a", help="Exact text to replace.")],
    replacement: Annotated[str, typer.Option("--replacement", "-r", help="Replacement text.")],
    occurrence: Annotated[
        int,
        typer.Option("--occurrence", "-n", help="One-based anchor occurrence."),
    ] = 1,
    if_match: Annotated[
        str | None,
        typer.Option("--if-match", help="Expected current SHA256 before writing."),
    ] = None,
    timeout: Annotated[float, typer.Option("--timeout", help="Timeout in seconds.")] = 60.0,
) -> None:
    """Replace the Nth exact anchor occurrence."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        script_edit_anchor(
            state.bridge,
            path,
            anchor=anchor,
            replacement=replacement,
            occurrence=occurrence,
            if_match=if_match,
            timeout=timeout,
        )
    )
    print_result(result, state.formatter)

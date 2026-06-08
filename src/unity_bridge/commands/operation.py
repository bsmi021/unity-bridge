"""Operation ledger commands."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult
from unity_bridge.core.operation import OperationStore

operation_app = typer.Typer(name="operation", help="Inspect durable bridge operations.")


async def operation_status(project_root: Path, command_id: str) -> CommandResult:
    """Return the persisted operation record for a command ID."""
    store = OperationStore(project_root)
    record = store.load(command_id)
    if record is None:
        return CommandResult(
            success=False,
            data={"commandId": command_id, "status": "not_found"},
            error=f"Operation not found: {command_id}",
            exit_code=2,
        )
    return CommandResult(success=True, data=record.to_dict())


async def operation_list(
    project_root: Path,
    include_terminal: bool = False,
    limit: int = 50,
) -> CommandResult:
    """List persisted operation records."""
    store = OperationStore(project_root)
    records = store.list_records(include_terminal=include_terminal, limit=limit)
    return CommandResult(
        success=True,
        data={
            "count": len(records),
            "operations": [record.to_dict() for record in records],
        },
    )


@operation_app.command("status")
def operation_status_cli(
    ctx: typer.Context,
    command_id: Annotated[str, typer.Argument(help="Bridge command ID to inspect.")],
) -> None:
    """Show persisted lifecycle state for a bridge command."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(operation_status(state.project_root, command_id))
    print_result(result, state.formatter)


@operation_app.command("list")
def operation_list_cli(
    ctx: typer.Context,
    include_terminal: Annotated[
        bool,
        typer.Option("--include-terminal", help="Include completed/failed operations."),
    ] = False,
    limit: Annotated[int, typer.Option("--limit", help="Maximum records to show.")] = 50,
) -> None:
    """List persisted bridge operations."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(operation_list(state.project_root, include_terminal, limit))
    print_result(result, state.formatter)

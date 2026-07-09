"""Operation ledger commands."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult
from unity_bridge.core.operation import OperationStore
from unity_bridge.core.operation_control import (
    submit_operation,
    wait_operation,
)

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


async def operation_submit(
    project_root: Path,
    command_type: str,
    parameters: dict[str, object] | None,
    timeout: float = 30.0,
    client_policy: dict[str, object] | None = None,
) -> CommandResult:
    """Queue a bridge command without waiting for Unity readiness."""
    return submit_operation(
        project_root,
        command_type,
        parameters or {},
        timeout=timeout,
        client_policy=client_policy,
    )


async def operation_wait(
    project_root: Path,
    command_id: str,
    timeout: float = 30.0,
    poll_interval: float = 0.5,
) -> CommandResult:
    """Dispatch and poll a queued or in-flight operation."""
    return await wait_operation(
        project_root,
        command_id,
        timeout=timeout,
        poll_interval=poll_interval,
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


@operation_app.command("submit")
def operation_submit_cli(
    ctx: typer.Context,
    command_type: Annotated[str, typer.Argument(help="Raw bridge command type to queue.")],
    params_json: Annotated[
        str | None,
        typer.Option("--params-json", help="Command parameters as a JSON object."),
    ] = None,
    params_file: Annotated[
        Path | None,
        typer.Option("--params-file", help="Path to a JSON object parameter file."),
    ] = None,
    timeout: Annotated[float, typer.Option("--timeout", help="Command timeout in seconds.")] = 30.0,
) -> None:
    """Queue a bridge command and return a durable command id immediately."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    parameters = _load_parameters(params_json=params_json, params_file=params_file)
    if isinstance(parameters, CommandResult):
        print_result(parameters, state.formatter)
        return
    result = asyncio.run(operation_submit(state.project_root, command_type, parameters, timeout))
    print_result(result, state.formatter)


@operation_app.command("wait")
def operation_wait_cli(
    ctx: typer.Context,
    command_id: Annotated[str, typer.Argument(help="Bridge command ID to wait for.")],
    timeout: Annotated[float, typer.Option("--timeout", help="Caller wait timeout.")] = 30.0,
    poll_interval: Annotated[
        float,
        typer.Option("--poll-interval", help="Seconds between operation polls."),
    ] = 0.5,
) -> None:
    """Dispatch queued work and wait for terminal state or caller patience timeout."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        operation_wait(
            state.project_root,
            command_id,
            timeout=timeout,
            poll_interval=poll_interval,
        )
    )
    print_result(result, state.formatter)


def _load_parameters(
    *,
    params_json: str | None,
    params_file: Path | None,
) -> dict[str, object] | CommandResult:
    if params_json and params_file:
        return CommandResult(
            success=False,
            error="Use only one of --params-json or --params-file.",
            exit_code=3,
        )
    if params_file is not None:
        try:
            params_json = params_file.read_text(encoding="utf-8-sig")
        except OSError as exc:
            return CommandResult(success=False, error=str(exc), exit_code=3)
    if not params_json:
        return {}
    try:
        payload = json.loads(params_json)
    except json.JSONDecodeError as exc:
        return CommandResult(success=False, error=f"Invalid JSON: {exc}", exit_code=3)
    if not isinstance(payload, dict):
        return CommandResult(success=False, error="Parameters must be a JSON object.", exit_code=3)
    return payload

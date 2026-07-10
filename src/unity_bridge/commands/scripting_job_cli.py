"""Typer wrappers for cooperative script-job submission and cancellation."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer

from unity_bridge.commands.scripting import AssemblyIdentityRequest, _script_parameters
from unity_bridge.core.bridge import CommandResult, DirectBridge
from unity_bridge.core.operation_control import submit_operation


async def execute_script_job(
    bridge: DirectBridge,
    expression: str | None = None,
    file: Path | None = None,
    timeout: int = 30,
    *,
    intent: str = "read-only",
    expected_assemblies: list[str] | None = None,
    assembly_identities: list[AssemblyIdentityRequest] | None = None,
    declared_object_ids: list[str] | None = None,
    declared_file_paths: list[str] | None = None,
    undo_label: str | None = None,
    return_schema: str = "auto",
    allow_internal_reflection: bool = False,
) -> CommandResult:
    """Run a cooperative job, advancing one user step per Editor update."""
    parameters = _script_parameters(
        expression,
        file,
        intent=intent,
        expected_assemblies=expected_assemblies,
        assembly_identities=assembly_identities,
        declared_object_ids=declared_object_ids,
        declared_file_paths=declared_file_paths,
        undo_label=undo_label,
        return_schema=return_schema,
        allow_internal_reflection=allow_internal_reflection,
        timeout=timeout,
    )
    return await bridge.send_command_with_retry(
        command_type="execute-job",
        parameters={
            "expression": parameters["expression"],
            "returnValue": parameters["returnValue"],
            "manifest": parameters["manifest"],
        },
        timeout=float(timeout + 5),
    )


def detach_execute_script_job(
    project_root: Path,
    expression: str | None = None,
    file: Path | None = None,
    timeout: int = 30,
    **manifest_options: object,
) -> CommandResult:
    """Queue a cooperative job and return its command id immediately."""
    parameters = _script_parameters(
        expression,
        file,
        timeout=timeout,
        **manifest_options,
    )
    return submit_operation(
        project_root,
        "execute-job",
        parameters,
        timeout=float(timeout + 5),
    )


async def cancel_execute_script_job(
    bridge: DirectBridge,
    target_command_id: str,
) -> CommandResult:
    """Request cancellation before the target job's next cooperative step."""
    normalized = target_command_id.strip()
    if not normalized:
        raise ValueError("target_command_id is required.")
    return await bridge.send_command_with_retry(
        command_type="cancel-execute-job",
        parameters={"targetCommandId": normalized},
        timeout=10.0,
    )


def script_job_cli(
    ctx: typer.Context,
    expression: Annotated[
        str | None,
        typer.Argument(help="Expression returning an IExecuteScriptJob."),
    ] = None,
    file: Annotated[
        Path | None,
        typer.Option("--file", "-f", help="File containing the job factory expression."),
    ] = None,
    intent: Annotated[
        str,
        typer.Option("--intent", help="Execution intent: read-only or mutating."),
    ] = "read-only",
    assembly: Annotated[
        list[str],
        typer.Option("--assembly", help="Unique assembly simple name; repeat as needed."),
    ] = None,
    assembly_identity: Annotated[
        list[str],
        typer.Option(
            "--assembly-identity",
            help="Exact FULL_NAME|MVID|LOADED_PATH selector; repeat as needed.",
        ),
    ] = None,
    object_id: Annotated[
        list[str],
        typer.Option("--object-id", help="Declared GlobalObjectId mutation target."),
    ] = None,
    asset_path: Annotated[
        list[str],
        typer.Option("--asset-path", help="Declared canonical Assets/ mutation target."),
    ] = None,
    undo_label: Annotated[
        str | None,
        typer.Option("--undo-label", help="Required label for mutating jobs."),
    ] = None,
    return_schema: Annotated[
        str,
        typer.Option("--return-schema", help="Expected structured result schema."),
    ] = "auto",
    allow_internal_reflection: Annotated[
        bool,
        typer.Option("--allow-internal-reflection", help="Allow non-public reflection APIs."),
    ] = False,
    timeout: Annotated[
        int,
        typer.Option("--timeout", help="Unity-side cooperative deadline in seconds."),
    ] = 30,
    detach: Annotated[
        bool,
        typer.Option("--detach", help="Queue the job and return its command id."),
    ] = False,
) -> None:
    """Run a cooperative C# job one bounded step per Editor update."""
    from unity_bridge.commands.scripting import _parse_identity_option
    from unity_bridge.core.output import print_result

    try:
        identities = [_parse_identity_option(value) for value in assembly_identity or []]
        options = {
            "intent": intent,
            "expected_assemblies": assembly,
            "assembly_identities": identities,
            "declared_object_ids": object_id,
            "declared_file_paths": asset_path,
            "undo_label": undo_label,
            "return_schema": return_schema,
            "allow_internal_reflection": allow_internal_reflection,
        }
        state = ctx.obj
        result = (
            detach_execute_script_job(state.project_root, expression, file, timeout, **options)
            if detach
            else asyncio.run(execute_script_job(state.bridge, expression, file, timeout, **options))
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    print_result(result, state.formatter)


def script_cancel_cli(
    ctx: typer.Context,
    command_id: Annotated[
        str,
        typer.Argument(help="Command id of the active cooperative job."),
    ],
) -> None:
    """Request cancellation before the target job's next step."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    try:
        result = asyncio.run(cancel_execute_script_job(state.bridge, command_id))
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    print_result(result, state.formatter)

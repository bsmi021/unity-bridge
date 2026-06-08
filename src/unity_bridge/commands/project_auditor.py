"""Unity Project Auditor bridge commands."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge


def _csv(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [part.strip() for part in value.split(",") if part.strip()]


async def project_auditor_availability(
    bridge: DirectBridge,
    timeout: float = 10.0,
) -> CommandResult:
    """Report whether the Project Auditor package/API is available."""
    return await bridge.send_command_with_retry(
        command_type="project-auditor",
        parameters={"operation": "availability"},
        timeout=timeout,
    )


async def project_auditor_run(
    bridge: DirectBridge,
    *,
    output_path: str | None = None,
    max_issues: int | None = None,
    categories: list[str] | None = None,
    assembly_names: list[str] | None = None,
    platform: str | None = None,
    timeout: float = 300.0,
) -> CommandResult:
    """Run Project Auditor and return a summary."""
    params: dict[str, object] = {"operation": "run"}
    if output_path:
        params["outputPath"] = output_path
    if max_issues is not None:
        params["maxIssues"] = max_issues
    if categories:
        params["categories"] = categories
    if assembly_names:
        params["assemblyNames"] = assembly_names
    if platform:
        params["platform"] = platform
    return await bridge.send_command_with_retry(
        command_type="project-auditor",
        parameters=params,
        timeout=timeout,
    )


async def project_auditor_load(
    bridge: DirectBridge,
    output_path: str,
    *,
    max_issues: int | None = None,
    timeout: float = 30.0,
) -> CommandResult:
    """Load and summarize an existing Project Auditor report."""
    params: dict[str, object] = {"operation": "load", "outputPath": output_path}
    if max_issues is not None:
        params["maxIssues"] = max_issues
    return await bridge.send_command_with_retry(
        command_type="project-auditor",
        parameters=params,
        timeout=timeout,
    )


project_auditor_app = typer.Typer(
    name="project-auditor",
    help="Run and inspect Unity Project Auditor reports.",
)


@project_auditor_app.command("availability")
def availability_cli(ctx: typer.Context) -> None:
    """Check Project Auditor package/API availability."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(project_auditor_availability(state.bridge))
    print_result(result, state.formatter)


@project_auditor_app.command("run")
def run_cli(
    ctx: typer.Context,
    output_path: Annotated[
        str | None, typer.Option("--output", help="Optional JSON report output path.")
    ] = None,
    max_issues: Annotated[
        int | None, typer.Option("--max-issues", help="Maximum issues to return.")
    ] = 100,
    categories: Annotated[
        str | None, typer.Option("--categories", help="Comma-separated categories.")
    ] = None,
    assembly_names: Annotated[
        str | None, typer.Option("--assemblies", help="Comma-separated assemblies.")
    ] = None,
    platform: Annotated[
        str | None, typer.Option("--platform", help="Unity BuildTarget name.")
    ] = None,
) -> None:
    """Run Project Auditor."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        project_auditor_run(
            state.bridge,
            output_path=output_path,
            max_issues=max_issues,
            categories=_csv(categories),
            assembly_names=_csv(assembly_names),
            platform=platform,
        )
    )
    print_result(result, state.formatter)


@project_auditor_app.command("load")
def load_cli(
    ctx: typer.Context,
    output_path: Annotated[str, typer.Argument(help="Project Auditor JSON path.")],
    max_issues: Annotated[
        int | None, typer.Option("--max-issues", help="Maximum issues to return.")
    ] = 100,
) -> None:
    """Load and summarize a saved Project Auditor report."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        project_auditor_load(state.bridge, output_path, max_issues=max_issues)
    )
    print_result(result, state.formatter)

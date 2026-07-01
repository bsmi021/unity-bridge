"""Unity Code Coverage utility commands."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

CODE_COVERAGE_PACKAGE = "com.unity.testtools.codecoverage"

VALID_OPERATIONS = frozenset(
    {
        "availability",
        "install",
        "start-recording",
        "pause-recording",
        "resume-recording",
        "stop-recording",
        "find-reports",
        "summarize",
    }
)


async def code_coverage_operation(
    bridge: DirectBridge,
    action: str,
    *,
    version: str | None = None,
    report_path: str | None = None,
    max_results: int | None = None,
    timeout: float = 120.0,
) -> CommandResult:
    """Run a Code Coverage bridge operation.

    The bridge command is optional-package safe: availability and report
    inspection work even when the Unity Code Coverage package is missing.
    """
    normalised = action.lower().strip()
    if normalised not in VALID_OPERATIONS:
        raise ValueError(
            f"Invalid code coverage operation '{action}'. "
            f"Must be one of: {', '.join(sorted(VALID_OPERATIONS))}"
        )

    params: dict[str, object] = {"operation": normalised}
    if normalised == "install":
        params["identifier"] = (
            f"{CODE_COVERAGE_PACKAGE}@{version}" if version else CODE_COVERAGE_PACKAGE
        )
    if report_path is not None:
        params["reportPath"] = report_path
    if max_results is not None:
        params["maxResults"] = max_results

    return await bridge.send_command_with_retry(
        command_type="code-coverage",
        parameters=params,
        timeout=timeout,
    )


coverage_app = typer.Typer(
    name="coverage",
    help="Unity Code Coverage package utilities.",
)


@coverage_app.command("availability")
def availability_cli(ctx: typer.Context) -> None:
    """Check Code Coverage package/API availability."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(code_coverage_operation(state.bridge, "availability"))
    print_result(result, state.formatter)


@coverage_app.command("install")
def install_cli(
    ctx: typer.Context,
    version: Annotated[
        str | None,
        typer.Option("--version", help="Optional package version to install."),
    ] = None,
) -> None:
    """Install the Unity Code Coverage package through Package Manager."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(code_coverage_operation(state.bridge, "install", version=version))
    print_result(result, state.formatter)


@coverage_app.command("start")
def start_recording_cli(ctx: typer.Context) -> None:
    """Start an on-demand coverage recording session."""
    _recording_cli(ctx, "start-recording")


@coverage_app.command("pause")
def pause_recording_cli(ctx: typer.Context) -> None:
    """Pause the current coverage recording session."""
    _recording_cli(ctx, "pause-recording")


@coverage_app.command("resume")
def resume_recording_cli(ctx: typer.Context) -> None:
    """Resume a paused coverage recording session."""
    _recording_cli(ctx, "resume-recording")


@coverage_app.command("stop")
def stop_recording_cli(ctx: typer.Context) -> None:
    """Stop the current coverage recording session and let the package generate reports."""
    _recording_cli(ctx, "stop-recording")


@coverage_app.command("find-reports")
def find_reports_cli(
    ctx: typer.Context,
    path: Annotated[
        str | None,
        typer.Option("--path", help="Coverage root or file path to inspect."),
    ] = None,
    max_results: Annotated[
        int,
        typer.Option("--max-results", help="Maximum report artifacts to return."),
    ] = 50,
) -> None:
    """Find likely coverage report artifacts."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        code_coverage_operation(
            state.bridge,
            "find-reports",
            report_path=path,
            max_results=max_results,
        )
    )
    print_result(result, state.formatter)


@coverage_app.command("summarize")
def summarize_cli(
    ctx: typer.Context,
    path: Annotated[
        str | None,
        typer.Argument(help="Summary.json, Summary.xml, or OpenCover XML path."),
    ] = None,
) -> None:
    """Summarize an existing coverage report artifact."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(
        code_coverage_operation(state.bridge, "summarize", report_path=path)
    )
    print_result(result, state.formatter)


def _recording_cli(ctx: typer.Context, operation: str) -> None:
    """Shared CLI wrapper for CodeCoverage recording operations."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(code_coverage_operation(state.bridge, operation))
    print_result(result, state.formatter)

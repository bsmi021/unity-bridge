"""Scripting command: execute C# expressions in Unity Editor."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async function (CLI + MCP)
# ---------------------------------------------------------------------------


async def execute_script(
    bridge: DirectBridge,
    expression: str | None = None,
    file: Path | None = None,
    timeout: int = 30,
) -> CommandResult:
    """Execute a C# expression or script file in the Unity Editor.

    Exactly one of *expression* or *file* must be provided.

    Args:
        bridge: Active bridge connection.
        expression: C# expression or statements to execute.
        file: Path to a ``.cs`` file whose contents will be executed.
        timeout: Timeout in seconds.

    Raises:
        ValueError: If both or neither of expression/file are provided.
    """
    code = _resolve_code(expression, file)

    return await bridge.send_command_with_retry(
        command_type="execute-script",
        parameters={
            "expression": code,
            "returnValue": True,
        },
        timeout=float(timeout),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_code(expression: str | None, file: Path | None) -> str:
    """Determine the code to execute from either an expression or a file."""
    if expression and file:
        raise ValueError("Provide either an expression or --file, not both.")
    if file is not None:
        if not file.is_file():
            raise ValueError(f"Script file not found: {file}")
        return file.read_text(encoding="utf-8")
    if expression:
        return expression
    raise ValueError("Provide a C# expression or use --file to load from a file.")


# ---------------------------------------------------------------------------
# Typer CLI wrapper
# ---------------------------------------------------------------------------

script_app = typer.Typer(name="script", help="Execute C# expressions in Unity Editor.")


@script_app.callback(invoke_without_command=True)
def script_cli(
    ctx: typer.Context,
    expression: Annotated[
        str | None,
        typer.Argument(help="C# expression or statements to execute."),
    ] = None,
    file: Annotated[
        Path | None,
        typer.Option("--file", "-f", help="Path to a .cs file to execute."),
    ] = None,
    timeout: Annotated[
        int,
        typer.Option("--timeout", help="Timeout in seconds."),
    ] = 30,
) -> None:
    """Execute a C# expression in the Unity Editor."""
    from unity_bridge.core.output import print_result

    if expression is None and file is None:
        raise typer.BadParameter(
            "Provide a C# expression as an argument or use --file."
        )

    state = ctx.obj
    result = asyncio.run(execute_script(state.bridge, expression, file, timeout))
    print_result(result, state.formatter)

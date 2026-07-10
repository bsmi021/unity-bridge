"""Scripting command: execute C# expressions in Unity Editor."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated
from uuid import UUID

import typer

from unity_bridge.core.bridge import CommandResult, DirectBridge

# ---------------------------------------------------------------------------
# Core async function
# ---------------------------------------------------------------------------

SCRIPT_INTENTS = frozenset({"read-only", "mutating"})
RETURN_SCHEMAS = frozenset(
    {"auto", "void", "scalar", "collection", "dictionary", "unity-object", "dto"}
)


@dataclass(frozen=True, slots=True)
class AssemblyIdentityRequest:
    """Exact identity of one loaded managed assembly."""

    full_name: str
    mvid: str
    path: Path


async def execute_script(
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
    """Execute a C# expression or script file in the Unity Editor.

    Exactly one of *expression* or *file* must be provided.

    Args:
        bridge: Active bridge connection.
        expression: C# expression or statements to execute.
        file: Path to a ``.cs`` file whose contents will be executed.
        intent: Execution intent, either ``read-only`` or ``mutating``.
        expected_assemblies: Unique loaded assembly simple names the script requires.
        assembly_identities: Full name, MVID, and loaded path selectors for duplicates.
        declared_object_ids: Stable GlobalObjectId values allowed to change.
        declared_file_paths: Canonical Assets/ paths allowed to change.
        undo_label: Required Undo group label for mutating scripts.
        return_schema: Requested structured result shape.
        allow_internal_reflection: Permit explicit non-public reflection APIs.
        timeout: Timeout in seconds.

    Raises:
        ValueError: If both or neither of expression/file are provided.
    """
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
        command_type="execute-script",
        parameters={
            "expression": parameters["expression"],
            "returnValue": parameters["returnValue"],
            "manifest": parameters["manifest"],
        },
        timeout=float(timeout),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _script_parameters(
    expression: str | None,
    file: Path | None,
    *,
    intent: str = "read-only",
    expected_assemblies: list[str] | None = None,
    assembly_identities: list[AssemblyIdentityRequest] | None = None,
    declared_object_ids: list[str] | None = None,
    declared_file_paths: list[str] | None = None,
    undo_label: str | None = None,
    return_schema: str = "auto",
    allow_internal_reflection: bool = False,
    timeout: int = 30,
) -> dict[str, object]:
    code = _resolve_code(expression, file)
    manifest = _build_manifest(
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
    return {"expression": code, "returnValue": True, "manifest": manifest}


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


def _build_manifest(
    *,
    intent: str,
    expected_assemblies: list[str] | None,
    assembly_identities: list[AssemblyIdentityRequest] | None,
    declared_object_ids: list[str] | None,
    declared_file_paths: list[str] | None,
    undo_label: str | None,
    return_schema: str,
    allow_internal_reflection: bool,
    timeout: int,
) -> dict[str, object]:
    normalized_intent = intent.strip().lower()
    if normalized_intent not in SCRIPT_INTENTS:
        raise ValueError(f"Invalid intent '{intent}'. Expected read-only or mutating.")
    if timeout <= 0 or timeout > 3600:
        raise ValueError("timeout must be between 1 and 3600 seconds.")

    normalized_schema = return_schema.strip().lower()
    if normalized_schema not in RETURN_SCHEMAS:
        raise ValueError(f"Invalid return_schema '{return_schema}'.")

    assemblies = [name.strip() for name in expected_assemblies or []]
    if any(not name for name in assemblies):
        raise ValueError("expected_assemblies cannot contain an empty assembly name.")
    if len(set(assemblies)) != len(assemblies):
        raise ValueError("expected_assemblies contains a duplicate assembly name.")
    identities = _normalize_identity_requests(assembly_identities)
    object_ids = _normalize_declared_values(declared_object_ids, "declared_object_ids")
    file_paths = _normalize_declared_values(declared_file_paths, "declared_file_paths")

    normalized_undo_label = (undo_label or "").strip()
    if normalized_intent == "mutating" and not normalized_undo_label:
        raise ValueError("undo_label is required when intent is mutating.")
    if normalized_intent == "mutating" and not object_ids and not file_paths:
        raise ValueError("mutating intent requires at least one declared object or file target.")

    return {
        "intent": normalized_intent,
        "expectedAssemblies": assemblies,
        "expectedAssemblyIdentities": identities,
        "declaredObjectIds": object_ids,
        "declaredFilePaths": file_paths,
        "timeoutMs": timeout * 1000,
        "undoLabel": normalized_undo_label,
        "returnSchema": normalized_schema,
        "allowInternalReflection": allow_internal_reflection,
    }


def _normalize_declared_values(values: list[str] | None, option_name: str) -> list[str]:
    normalized = [value.strip() for value in values or []]
    if any(not value for value in normalized):
        raise ValueError(f"{option_name} cannot contain an empty value.")
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{option_name} contains a duplicate value.")
    return normalized


def _normalize_identity_requests(
    requests: list[AssemblyIdentityRequest] | None,
) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for request in requests or []:
        if not isinstance(request, AssemblyIdentityRequest):
            raise ValueError("assembly_identities must contain AssemblyIdentityRequest values.")
        identity = _normalize_identity_request(request)
        key = (
            identity["fullName"],
            identity["mvid"],
            identity["path"].casefold(),
        )
        if key in seen:
            raise ValueError("assembly_identities contains a duplicate identity.")
        seen.add(key)
        normalized.append(identity)
    return normalized


def _normalize_identity_request(request: AssemblyIdentityRequest) -> dict[str, str]:
    full_name = request.full_name.strip()
    if not full_name or "," not in full_name:
        raise ValueError("assembly identity full_name must be an assembly full name.")
    try:
        mvid = str(UUID(request.mvid.strip()))
    except (AttributeError, ValueError) as exc:
        raise ValueError("assembly identity mvid must be a UUID.") from exc
    path = Path(request.path).expanduser().resolve().as_posix()
    return {"fullName": full_name, "mvid": mvid, "path": path}


def _parse_identity_option(value: str) -> AssemblyIdentityRequest:
    parts = value.split("|", 2)
    if len(parts) != 3:
        raise ValueError("Expected FULL_NAME|MVID|LOADED_PATH.")
    return AssemblyIdentityRequest(full_name=parts[0], mvid=parts[1], path=Path(parts[2]))


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
    intent: Annotated[
        str,
        typer.Option("--intent", help="Execution intent: read-only or mutating."),
    ] = "read-only",
    assembly: Annotated[
        list[str],
        typer.Option(
            "--assembly",
            help="Unique loaded assembly simple name; repeat as needed.",
        ),
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
        typer.Option(
            "--object-id",
            help="Declared GlobalObjectId mutation target; repeat as needed.",
        ),
    ] = None,
    asset_path: Annotated[
        list[str],
        typer.Option(
            "--asset-path",
            help="Declared canonical Assets/ file mutation target; repeat as needed.",
        ),
    ] = None,
    undo_label: Annotated[
        str | None,
        typer.Option("--undo-label", help="Undo group label required for mutating intent."),
    ] = None,
    return_schema: Annotated[
        str,
        typer.Option(
            "--return-schema",
            help="Expected result: auto, void, scalar, collection, dictionary, unity-object, dto.",
        ),
    ] = "auto",
    allow_internal_reflection: Annotated[
        bool,
        typer.Option(
            "--allow-internal-reflection",
            help="Allow explicit non-public reflection APIs.",
        ),
    ] = False,
    timeout: Annotated[
        int,
        typer.Option("--timeout", help="Timeout in seconds."),
    ] = 30,
) -> None:
    """Execute a C# expression in the Unity Editor."""
    from unity_bridge.core.output import print_result

    if expression is None and file is None:
        raise typer.BadParameter("Provide a C# expression as an argument or use --file.")

    state = ctx.obj
    try:
        exact_assemblies = [_parse_identity_option(value) for value in assembly_identity or []]
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--assembly-identity") from exc
    result = asyncio.run(
        execute_script(
            state.bridge,
            expression,
            file,
            intent=intent,
            expected_assemblies=assembly,
            assembly_identities=exact_assemblies,
            declared_object_ids=object_id,
            declared_file_paths=asset_path,
            undo_label=undo_label,
            return_schema=return_schema,
            allow_internal_reflection=allow_internal_reflection,
            timeout=timeout,
        )
    )
    print_result(result, state.formatter)

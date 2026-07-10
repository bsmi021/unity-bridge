"""Exact loaded-assembly probes for the Unity API coverage registry."""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

import typer

from unity_bridge.commands.scripting import AssemblyIdentityRequest, execute_script
from unity_bridge.core.bridge import CommandResult, DirectBridge


LIST_IDENTITIES_EXPRESSION = """
System.AppDomain.CurrentDomain.GetAssemblies()
    .Where(assembly => !assembly.IsDynamic
        && !string.IsNullOrEmpty(assembly.Location)
        && !string.IsNullOrEmpty(assembly.FullName)
        && !string.IsNullOrEmpty(assembly.GetName().Name))
    .Select(assembly => new BWS.Editor.ClaudeCodeBridge.ExecuteScriptAssemblyIdentity {
        name = assembly.GetName().Name,
        fullName = assembly.FullName,
        mvid = assembly.ManifestModule.ModuleVersionId.ToString("D"),
        path = assembly.Location
    })
    .OrderBy(identity => identity.name)
    .ThenBy(identity => identity.path)
    .ToArray()
""".strip()


@dataclass(frozen=True, slots=True)
class SnapshotAssembly:
    name: str
    path: str
    mvid: str
    sha256: str


@dataclass(frozen=True, slots=True)
class LoadedAssembly:
    name: str
    full_name: str
    mvid: str
    path: Path


async def probe_snapshot_assemblies(
    bridge: DirectBridge,
    snapshot: Path,
    *,
    timeout: int = 30,
) -> CommandResult:
    """Exact-reference every loaded assembly present in one inventory snapshot."""
    try:
        snapshot_hash, unity_version, assemblies = _load_snapshot(snapshot)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return CommandResult(success=False, error=str(exc), exit_code=1)
    listed = await execute_script(
        bridge,
        expression=LIST_IDENTITIES_EXPRESSION,
        return_schema="collection",
        timeout=timeout,
    )
    if not listed.success:
        return listed
    try:
        loaded = _parse_loaded_assemblies(listed.data)
    except ValueError as exc:
        return CommandResult(success=False, error=str(exc), exit_code=1)

    proven: list[dict[str, object]] = []
    unproven: list[dict[str, str]] = []
    for assembly in assemblies:
        await _probe_one(bridge, assembly, loaded, timeout, proven, unproven)
    proof = _proof_manifest(snapshot_hash, unity_version, proven)
    data = {
        "proof": proof,
        "assembly_count": len(assemblies),
        "proven_count": len(proven),
        "unproven_count": len(unproven),
        "unproven": unproven,
    }
    if unproven:
        return CommandResult(
            success=False,
            data=data,
            error=f"{len(unproven)} snapshot assemblies lack exact live compile proof.",
            exit_code=1,
        )
    return CommandResult(success=True, data=data)


async def _probe_one(
    bridge: DirectBridge,
    assembly: SnapshotAssembly,
    loaded: dict[tuple[str, str], LoadedAssembly],
    timeout: int,
    proven: list[dict[str, object]],
    unproven: list[dict[str, str]],
) -> None:
    identity = loaded.get((assembly.name, assembly.mvid))
    if identity is None:
        unproven.append(_unproven(assembly, "exact_identity_not_loaded"))
        return
    try:
        live_hash = hashlib.sha256(identity.path.read_bytes()).hexdigest()
    except OSError:
        unproven.append(_unproven(assembly, "loaded_file_unreadable"))
        return
    if live_hash != assembly.sha256:
        unproven.append(_unproven(assembly, "loaded_file_hash_mismatch"))
        return
    result = await execute_script(
        bridge,
        expression="1",
        assembly_identities=[
            AssemblyIdentityRequest(identity.full_name, identity.mvid, identity.path)
        ],
        return_schema="scalar",
        timeout=timeout,
    )
    if not result.success:
        failure = _unproven(assembly, "exact_identity_compile_failed")
        failure["details"] = result.error or "generic host returned no error detail"
        unproven.append(failure)
        return
    proven.append(_proof_record(identity, live_hash))


def _load_snapshot(path: Path) -> tuple[str, str, list[SnapshotAssembly]]:
    contents = path.read_bytes()
    versions: set[str] = set()
    assemblies: dict[tuple[str, str, str], SnapshotAssembly] = {}
    for raw_line in contents.splitlines():
        if not raw_line.strip():
            continue
        record = json.loads(raw_line)
        version = record.get("context", {}).get("unity", {}).get("version")
        assembly = record.get("assembly")
        if not isinstance(version, str) or not isinstance(assembly, dict):
            raise ValueError("Snapshot records require context.unity.version and assembly.")
        item = _snapshot_assembly(assembly)
        versions.add(version)
        assemblies[(item.name, item.mvid, item.sha256)] = item
    if len(versions) != 1 or not assemblies:
        raise ValueError("Snapshot must contain assemblies for exactly one Unity version.")
    ordered = sorted(assemblies.values(), key=lambda item: (item.name, item.mvid, item.path))
    return hashlib.sha256(contents).hexdigest(), versions.pop(), ordered


def _snapshot_assembly(value: dict[str, Any]) -> SnapshotAssembly:
    required = ("name", "path", "mvid", "sha256")
    if any(not isinstance(value.get(key), str) or not value[key] for key in required):
        raise ValueError("Snapshot assembly identity is incomplete.")
    return SnapshotAssembly(
        name=value["name"],
        path=value["path"],
        mvid=value["mvid"].lower(),
        sha256=value["sha256"].lower(),
    )


def _parse_loaded_assemblies(data: object) -> dict[tuple[str, str], LoadedAssembly]:
    if not isinstance(data, dict):
        raise ValueError("Loaded assembly probe returned no structured data.")
    value = data.get("value")
    if not isinstance(value, dict) or value.get("kind") != "collection":
        raise ValueError("Loaded assembly probe did not return a collection.")
    loaded: dict[tuple[str, str], LoadedAssembly] = {}
    for item in value.get("items", []):
        fields = _dto_fields(item)
        identity = LoadedAssembly(
            name=fields["name"],
            full_name=fields["fullName"],
            mvid=fields["mvid"].lower(),
            path=Path(fields["path"]).expanduser().resolve(),
        )
        loaded[(identity.name, identity.mvid)] = identity
    return loaded


def _dto_fields(value: object) -> dict[str, str]:
    if not isinstance(value, dict) or value.get("kind") != "dto":
        raise ValueError("Loaded assembly identity is not a DTO.")
    fields: dict[str, str] = {}
    for field in value.get("fields", []):
        if not isinstance(field, dict) or not isinstance(field.get("value"), dict):
            raise ValueError("Loaded assembly identity field is malformed.")
        field_value = field["value"]
        text = field_value.get("string_value", field_value.get("stringValue", ""))
        fields[str(field.get("name"))] = str(text)
    if any(not fields.get(name) for name in ("name", "fullName", "mvid", "path")):
        raise ValueError("Loaded assembly identity is incomplete.")
    return fields


def _proof_record(identity: LoadedAssembly, sha256: str) -> dict[str, object]:
    return {
        "name": identity.name,
        "path": identity.path.as_posix(),
        "mvid": identity.mvid,
        "sha256": sha256,
        "proof": [
            "csharp_compile:execute-script-exact-identity",
            "live_positive:unity-{version}-exact-assembly",
        ],
    }


def _proof_manifest(
    snapshot_hash: str,
    unity_version: str,
    assemblies: list[dict[str, object]],
) -> dict[str, object]:
    live_label = f"live_positive:unity-{unity_version}-exact-assembly"
    for assembly in assemblies:
        assembly["proof"] = [
            "csharp_compile:execute-script-exact-identity",
            live_label,
        ]
    return {
        "schema_version": "1.0",
        "snapshot": {"sha256": snapshot_hash, "unity_version": unity_version},
        "assemblies": assemblies,
    }


def _unproven(assembly: SnapshotAssembly, reason: str) -> dict[str, str]:
    return {"name": assembly.name, "mvid": assembly.mvid, "reason": reason}


def script_probe_assemblies_cli(
    ctx: typer.Context,
    snapshot: Annotated[
        Path,
        typer.Argument(help="Inventory JSONL snapshot to prove exactly."),
    ],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Write the generic proof manifest as JSON."),
    ] = None,
    timeout: Annotated[
        int,
        typer.Option("--timeout", help="Per-assembly compiler probe timeout."),
    ] = 30,
) -> None:
    """Exact-reference every loaded assembly in an inventory snapshot."""
    from unity_bridge.core.output import print_result

    state = ctx.obj
    result = asyncio.run(probe_snapshot_assemblies(state.bridge, snapshot, timeout=timeout))
    if output is not None and isinstance(result.data, dict):
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(result.data["proof"], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        result.data["proof_output"] = str(output.resolve())
    print_result(result, state.formatter)

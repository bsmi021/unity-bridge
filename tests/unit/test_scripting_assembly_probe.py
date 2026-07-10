"""Contracts for exact loaded-assembly generic-host proof generation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from unity_bridge.core.bridge import CommandResult


def _dto_identity(name: str, full_name: str, mvid: str, path: Path) -> dict[str, object]:
    fields = []
    for field_name, value in (
        ("name", name),
        ("fullName", full_name),
        ("mvid", mvid),
        ("path", str(path)),
    ):
        fields.append(
            {
                "name": field_name,
                "value": {"kind": "string", "string_value": value},
            }
        )
    return {"kind": "dto", "fields": fields}


@pytest.mark.asyncio
async def test_probe_promotes_only_exact_hash_matching_loaded_assemblies(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Arrange
    from unity_bridge.commands import scripting_assembly_probe as probe

    assembly_path = tmp_path / "UnityEditor.CoreModule.dll"
    assembly_path.write_bytes(b"exact-runtime-module")
    assembly_hash = hashlib.sha256(assembly_path.read_bytes()).hexdigest()
    mvid = "11111111-1111-1111-1111-111111111111"
    snapshot = tmp_path / "snapshot.jsonl"
    snapshot.write_text(
        json.dumps(
            {
                "symbol_id": "UnityEditor.CoreModule::T:Fixture",
                "assembly": {
                    "name": "UnityEditor.CoreModule",
                    "path": "Editor/Data/Managed/UnityEngine/UnityEditor.CoreModule.dll",
                    "mvid": mvid,
                    "sha256": assembly_hash,
                },
                "context": {"unity": {"version": "6000.5.1f1"}},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    list_result = CommandResult(
        success=True,
        data={
            "value": {
                "kind": "collection",
                "items": [
                    _dto_identity(
                        "UnityEditor.CoreModule",
                        "UnityEditor.CoreModule, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null",
                        mvid,
                        assembly_path,
                    )
                ],
            }
        },
    )
    exact_result = CommandResult(
        success=True,
        data={"success": True, "compiler_diagnostics": []},
    )
    execute = AsyncMock(side_effect=[list_result, exact_result])
    monkeypatch.setattr(probe, "execute_script", execute)

    # Act
    result = await probe.probe_snapshot_assemblies(object(), snapshot, timeout=10)

    # Assert
    assert result.success is True
    proof = result.data["proof"]
    assert proof["snapshot"] == {
        "sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
        "unity_version": "6000.5.1f1",
    }
    assert proof["assemblies"] == [
        {
            "name": "UnityEditor.CoreModule",
            "path": str(assembly_path.resolve()).replace("\\", "/"),
            "mvid": mvid,
            "sha256": assembly_hash,
            "proof": [
                "csharp_compile:execute-script-exact-identity",
                "live_positive:unity-6000.5.1f1-exact-assembly",
            ],
        }
    ]
    assert result.data["unproven"] == []
    identity = execute.await_args_list[1].kwargs["assembly_identities"][0]
    assert identity.full_name.startswith("UnityEditor.CoreModule,")
    assert identity.mvid == mvid
    assert identity.path == assembly_path.resolve()


@pytest.mark.asyncio
async def test_probe_reports_loaded_identity_hash_mismatch_without_compiling(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Arrange
    from unity_bridge.commands import scripting_assembly_probe as probe

    assembly_path = tmp_path / "UnityEditor.GIModule.dll"
    assembly_path.write_bytes(b"different-build")
    mvid = "22222222-2222-2222-2222-222222222222"
    snapshot = tmp_path / "snapshot.jsonl"
    snapshot.write_text(
        json.dumps(
            {
                "symbol_id": "UnityEditor.GIModule::T:Fixture",
                "assembly": {
                    "name": "UnityEditor.GIModule",
                    "path": "Editor/Data/Managed/UnityEngine/UnityEditor.GIModule.dll",
                    "mvid": mvid,
                    "sha256": "a" * 64,
                },
                "context": {"unity": {"version": "6000.5.1f1"}},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    list_result = CommandResult(
        success=True,
        data={
            "value": {
                "kind": "collection",
                "items": [
                    _dto_identity(
                        "UnityEditor.GIModule",
                        "UnityEditor.GIModule, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null",
                        mvid,
                        assembly_path,
                    )
                ],
            }
        },
    )
    execute = AsyncMock(return_value=list_result)
    monkeypatch.setattr(probe, "execute_script", execute)

    # Act
    result = await probe.probe_snapshot_assemblies(object(), snapshot, timeout=10)

    # Assert
    assert result.success is False
    assert result.data["proof"]["assemblies"] == []
    assert result.data["unproven"] == [
        {
            "name": "UnityEditor.GIModule",
            "mvid": mvid,
            "reason": "loaded_file_hash_mismatch",
        }
    ]
    assert execute.await_count == 1

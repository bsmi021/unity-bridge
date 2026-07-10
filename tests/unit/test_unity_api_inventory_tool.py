from __future__ import annotations

import json
import hashlib
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[2]
TOOL_PROJECT = ROOT / "tools" / "UnityApiInventory" / "UnityApiInventory.csproj"
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "unity_api_inventory"
FIXED_CAPTURE_TIME = "2026-07-10T12:00:00Z"


@pytest.fixture(scope="session")
def inventory_tool(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the standalone metadata tool once for black-box tests."""
    # Arrange
    assert TOOL_PROJECT.is_file(), f"inventory tool project is missing: {TOOL_PROJECT}"
    output_dir = tmp_path_factory.mktemp("inventory-tool")

    # Act
    result = subprocess.run(
        [
            "dotnet",
            "build",
            str(TOOL_PROJECT),
            "--configuration",
            "Release",
            "--output",
            str(output_dir),
            "--nologo",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    # Assert
    assert result.returncode == 0, result.stdout + result.stderr
    tool = output_dir / "UnityApiInventory.dll"
    assert tool.is_file()
    return tool


@pytest.fixture(scope="session")
def fixture_assemblies(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """Compile deterministic test metadata without a Unity installation."""
    # Arrange
    workspace = tmp_path_factory.mktemp("inventory-assemblies")
    source = workspace / "source"
    shutil.copytree(FIXTURE_ROOT, source)
    output = workspace / "output"

    # Act
    result = subprocess.run(
        [
            "dotnet",
            "build",
            str(source / "PublicSurface" / "PublicSurface.csproj"),
            "--configuration",
            "Release",
            "--output",
            str(output),
            "--nologo",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    # Assert
    assert result.returncode == 0, result.stdout + result.stderr
    for project_name in ("TestSurface", "RegistrySurface", "DefaultProject"):
        result = subprocess.run(
            [
                "dotnet",
                "build",
                str(source / project_name / f"{project_name}.csproj"),
                "--configuration",
                "Release",
                "--output",
                str(output),
                "--nologo",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
    return {
        "public": output / "PublicSurface.dll",
        "forward_target": output / "ForwardTarget.dll",
        "test": output / "TestSurface.dll",
        "registry": output / "RegistrySurface.dll",
        "default": output / "Assembly-CSharp.dll",
    }


def _run_tool(tool: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["dotnet", str(tool), *arguments],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    lines = [json.dumps(record, sort_keys=True, separators=(",", ":")) for record in records]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _record(
    symbol_id: str,
    *,
    canonical_signature: str | None = None,
    is_static: bool = False,
    obsolete: bool = False,
    availability: str = "all",
    assembly: dict[str, str] | None = None,
) -> dict[str, Any]:
    record = {
        "schema_version": "1.0",
        "symbol_id": symbol_id,
        "canonical_signature": canonical_signature or symbol_id,
        "record_kind": "method",
        "member_kind": "method",
        "is_static": is_static,
        "generic_arity": 0,
        "obsolete": {
            "is_obsolete": obsolete,
            "message": "obsolete" if obsolete else None,
            "is_error": False,
        },
        "availability": {"key": availability},
        "provenance": {"classification": "unity_runtime"},
    }
    if assembly is not None:
        record["assembly"] = assembly
    return record


def test_inventory_extracts_canonical_public_surface_deterministically(
    inventory_tool: Path,
    fixture_assemblies: dict[str, Path],
    tmp_path: Path,
) -> None:
    # Arrange
    unity_root = tmp_path / "Unity" / "6000.5.1f1"
    managed = unity_root / "Editor" / "Data" / "Managed" / "UnityEngine"
    managed.mkdir(parents=True)
    for assembly in fixture_assemblies.values():
        shutil.copy2(assembly, managed / assembly.name)
    shutil.copy2(
        fixture_assemblies["public"],
        managed.parent / "UnityEditor.InternalImplementation.dll",
    )
    native_module = (
        unity_root
        / "Editor"
        / "Data"
        / "PlaybackEngines"
        / "WindowsStandaloneSupport"
        / "Variations"
        / "mono"
        / "Managed"
        / "native-only.dll"
    )
    native_module.parent.mkdir(parents=True)
    native_module.write_bytes(b"not a managed PE fixture")
    irrelevant_native = (
        unity_root
        / "Editor"
        / "Data"
        / "PlaybackEngines"
        / "WindowsStandaloneSupport"
        / "Tools"
        / "irrelevant-native.dll"
    )
    irrelevant_native.parent.mkdir(parents=True)
    irrelevant_native.write_bytes(b"not part of public managed metadata")
    first_snapshot = tmp_path / "first.jsonl"
    second_snapshot = tmp_path / "second.jsonl"
    first_summary = tmp_path / "first-summary.json"
    second_summary = tmp_path / "second-summary.json"
    common_arguments = (
        "inventory",
        "--unity-root",
        str(unity_root),
        "--unity-version",
        "6000.5.1f1",
        "--unity-revision",
        "abc123",
        "--capture-time",
        FIXED_CAPTURE_TIME,
        "--build-target",
        "StandaloneWindows64",
        "--api-compatibility",
        "NET_Standard_2_1",
        "--toc-js",
        str(FIXTURE_ROOT / "toc.js"),
        "--documentation-base-url",
        "https://docs.example.test/6000.5/ScriptReference",
        "--define",
        "UNITY_EDITOR",
        "--assembly",
        str(managed / fixture_assemblies["public"].name),
        "--assembly",
        str(managed / fixture_assemblies["forward_target"].name),
        "--assembly",
        str(native_module),
    )

    # Act
    first = _run_tool(
        inventory_tool,
        *common_arguments,
        "--output",
        str(first_snapshot),
        "--summary",
        str(first_summary),
    )
    second = _run_tool(
        inventory_tool,
        *common_arguments,
        "--output",
        str(second_snapshot),
        "--summary",
        str(second_summary),
    )

    # Assert
    assert first.returncode == 0, first.stdout + first.stderr
    assert second.returncode == 0, second.stdout + second.stderr
    assert first_snapshot.read_bytes() == second_snapshot.read_bytes()
    assert first_summary.read_bytes() == second_summary.read_bytes()

    records = [json.loads(line) for line in first_snapshot.read_text().splitlines()]
    assert len({record["symbol_id"] for record in records}) == len(records)
    signatures = {record["canonical_signature"] for record in records}
    assert any("VisibleOuter+VisibleNested" in signature for signature in signatures)
    assert not any("HiddenNested" in signature for signature in signatures)
    assert not any("PublicButUnreachable" in signature for signature in signatures)

    ping_records = [
        record
        for record in records
        if record["member_kind"] == "method" and ".Ping(" in record["canonical_signature"]
    ]
    assert len(ping_records) == 2
    assert {record["canonical_signature"] for record in ping_records} == {
        "PublicSurface::FixtureApi.VisibleOuter+VisibleNested.Ping(System.Int32)->System.Void",
        "PublicSurface::FixtureApi.VisibleOuter+VisibleNested.Ping(System.String)->System.Void",
    }

    assert sum(record["member_kind"] == "property" for record in records) == 2
    assert sum(record["member_kind"] == "event" for record in records) == 1
    assert not any(
        token in record["canonical_signature"]
        for record in records
        if record["member_kind"] == "method"
        for token in (".get_", ".set_", ".add_", ".remove_")
    )

    legacy = next(record for record in records if ".Legacy(" in record["canonical_signature"])
    assert legacy["obsolete"] == {
        "is_obsolete": True,
        "message": "Use Ping instead.",
        "is_error": True,
    }
    echo = next(record for record in records if ".Echo``1(" in record["canonical_signature"])
    assert echo["is_static"] is True
    assert echo["generic_arity"] == 1
    assert "!!0&" in echo["canonical_signature"]

    forwarder = next(record for record in records if record["record_kind"] == "type_forwarder")
    assert forwarder["canonical_signature"] == "PublicSurface::ForwardTarget.ForwardedApi"
    visible_type = next(
        record
        for record in records
        if record["canonical_signature"] == "PublicSurface::FixtureApi.VisibleOuter"
    )
    visible_member = next(
        record
        for record in records
        if "+VisibleNested.Ping(System.Int32)" in record["canonical_signature"]
    )
    assert visible_type["documentation_url"] == (
        "https://docs.example.test/6000.5/ScriptReference/FixtureApi.VisibleOuter.html"
    )
    assert visible_member["documentation_url"] == (
        "https://docs.example.test/6000.5/ScriptReference/"
        "FixtureApi.VisibleOuter.VisibleNested.html"
    )
    engine_data = next(
        record
        for record in records
        if record["canonical_signature"].endswith("UnityEngine.Sprites.DataUtility")
    )
    editor_data = next(
        record
        for record in records
        if record["canonical_signature"].endswith("UnityEditor.Sprites.DataUtility")
    )
    assert engine_data["documentation_url"].endswith("/Sprites.DataUtility.html")
    assert editor_data["documentation_url"] is None

    summary = json.loads(first_summary.read_text(encoding="utf-8"))
    assert summary["unity"] == {"version": "6000.5.1f1", "revision": "abc123"}
    assert summary["capture_time"] == FIXED_CAPTURE_TIME
    assert summary["host_os"] == "windows"
    assert summary["assembly_count"] == 2
    assert summary["symbol_count"] == len(records)
    assert all(assembly["mvid"] and assembly["sha256"] for assembly in summary["assemblies"])
    assert all("Editor/Data/Managed/UnityEngine" in item["path"] for item in summary["assemblies"])
    assert summary["skipped_assemblies"] == [
        {
            "path": (
                "Editor/Data/PlaybackEngines/WindowsStandaloneSupport/Variations/"
                "mono/Managed/native-only.dll"
            ),
            "reason": "not_managed_assembly",
        }
    ]
    assert summary["documentation_join"] == {
        "status": "joined",
        "source_path": str(FIXTURE_ROOT / "toc.js").replace("\\", "/"),
        "source_sha256": summary["documentation_join"]["source_sha256"],
        "base_url": "https://docs.example.test/6000.5/ScriptReference",
        "toc_entry_count": 5,
        "indexed_entry_count": 5,
        "ignored_entry_count": 0,
        "ambiguous_identity_count": 0,
        "matched_type_count": 5,
        "unmatched_type_count": 1,
    }
    assert len(summary["documentation_join"]["source_sha256"]) == 64


def test_default_editor_inventory_uses_runtime_modules_not_reference_facade(
    inventory_tool: Path,
    fixture_assemblies: dict[str, Path],
    tmp_path: Path,
) -> None:
    # Arrange
    unity_root = tmp_path / "Unity" / "6000.5.1f1"
    managed = unity_root / "Editor" / "Data" / "Managed"
    modules = managed / "UnityEngine"
    modules.mkdir(parents=True)
    shutil.copy2(fixture_assemblies["public"], modules / "UnityEditor.CoreModule.dll")
    shutil.copy2(fixture_assemblies["forward_target"], modules / "UnityEditor.GIModule.dll")
    shutil.copy2(fixture_assemblies["registry"], modules / "UnityEngine.CoreModule.dll")
    shutil.copy2(fixture_assemblies["test"], managed / "UnityEditor.dll")
    snapshot = tmp_path / "snapshot.jsonl"
    summary_path = tmp_path / "summary.json"

    # Act
    result = _run_tool(
        inventory_tool,
        "inventory",
        "--unity-root",
        str(unity_root),
        "--unity-version",
        "6000.5.1f1",
        "--unity-revision",
        "abc123",
        "--capture-time",
        FIXED_CAPTURE_TIME,
        "--build-target",
        "StandaloneWindows64",
        "--api-compatibility",
        "NET_Standard_2_1",
        "--output",
        str(snapshot),
        "--summary",
        str(summary_path),
    )

    # Assert
    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    paths = {assembly["path"] for assembly in summary["assemblies"]}
    assert paths == {
        "Editor/Data/Managed/UnityEngine/UnityEditor.CoreModule.dll",
        "Editor/Data/Managed/UnityEngine/UnityEditor.GIModule.dll",
        "Editor/Data/Managed/UnityEngine/UnityEngine.CoreModule.dll",
    }


def test_snapshot_diff_reports_every_review_category_deterministically(
    inventory_tool: Path,
    tmp_path: Path,
) -> None:
    # Arrange
    before = tmp_path / "before.jsonl"
    after = tmp_path / "after.jsonl"
    first_output = tmp_path / "diff.json"
    second_output = tmp_path / "diff-again.json"
    _write_jsonl(
        before,
        [
            _record("Assembly::Removed"),
            _record("Assembly::Changed"),
            _record("Assembly::Obsolete"),
            _record("Assembly::Availability", availability="windows"),
        ],
    )
    _write_jsonl(
        after,
        [
            _record("Assembly::Added"),
            _record("Assembly::Changed", canonical_signature="Assembly::Changed->System.Int32"),
            _record("Assembly::Obsolete", obsolete=True),
            _record("Assembly::Availability", availability="linux"),
        ],
    )

    # Act
    first = _run_tool(
        inventory_tool,
        "diff",
        "--before",
        str(before),
        "--after",
        str(after),
        "--output",
        str(first_output),
    )
    second = _run_tool(
        inventory_tool,
        "diff",
        "--before",
        str(before),
        "--after",
        str(after),
        "--output",
        str(second_output),
    )

    # Assert
    assert first.returncode == 0, first.stdout + first.stderr
    assert second.returncode == 0, second.stdout + second.stderr
    assert first_output.read_bytes() == second_output.read_bytes()
    report = json.loads(first_output.read_text(encoding="utf-8"))
    assert report["counts"] == {
        "added": 1,
        "removed": 1,
        "changed": 1,
        "obsolete": 1,
        "availability_changed": 1,
    }
    assert report["added"][0]["symbol_id"] == "Assembly::Added"
    assert report["removed"][0]["symbol_id"] == "Assembly::Removed"
    assert report["changed"][0]["symbol_id"] == "Assembly::Changed"
    assert report["obsolete"][0]["symbol_id"] == "Assembly::Obsolete"
    assert report["availability_changed"][0]["symbol_id"] == "Assembly::Availability"


def test_coverage_gate_reports_unclassified_and_removed_symbols(
    inventory_tool: Path,
    tmp_path: Path,
) -> None:
    # Arrange
    snapshot = tmp_path / "snapshot.jsonl"
    registry = tmp_path / "coverage-registry.json"
    report_path = tmp_path / "coverage-report.json"
    _write_jsonl(snapshot, [_record("Assembly::Known"), _record("Assembly::Unclassified")])
    registry.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "records": [
                    {
                        "symbol_id": "Assembly::Known",
                        "classification": "typed",
                        "rationale": "Fixture typed path",
                        "proof": [],
                    },
                    {
                        "symbol_id": "Assembly::Removed",
                        "classification": "obsolete",
                        "rationale": "Removed fixture API",
                        "proof": [],
                    },
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # Act
    result = _run_tool(
        inventory_tool,
        "coverage-gate",
        "--snapshot",
        str(snapshot),
        "--registry",
        str(registry),
        "--output",
        str(report_path),
    )

    # Assert
    assert result.returncode == 3, result.stdout + result.stderr
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["classified_count"] == 1
    assert report["unclassified_symbol_ids"] == ["Assembly::Unclassified"]
    assert report["removed_registry_symbol_ids"] == ["Assembly::Removed"]
    assert report["is_complete"] is False


def test_coverage_gate_accepts_only_an_explicit_complete_registry(
    inventory_tool: Path,
    tmp_path: Path,
) -> None:
    # Arrange
    snapshot = tmp_path / "snapshot.jsonl"
    registry = tmp_path / "coverage-registry.json"
    report_path = tmp_path / "coverage-report.json"
    _write_jsonl(snapshot, [_record("Assembly::Known")])
    registry.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "records": [
                    {
                        "symbol_id": "Assembly::Known",
                        "classification": "public_unwrapped",
                        "rationale": "Explicitly awaiting a reachable path",
                        "proof": [],
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # Act
    result = _run_tool(
        inventory_tool,
        "coverage-gate",
        "--snapshot",
        str(snapshot),
        "--registry",
        str(registry),
        "--output",
        str(report_path),
    )

    # Assert
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["classified_count"] == 1
    assert report["unclassified_symbol_ids"] == []
    assert report["removed_registry_symbol_ids"] == []
    assert report["is_complete"] is True


def test_inventory_maps_asmdef_package_and_variant_provenance(
    inventory_tool: Path,
    fixture_assemblies: dict[str, Path],
    tmp_path: Path,
) -> None:
    # Arrange
    unity_root = tmp_path / "Unity" / "6000.5.1f1"
    (unity_root / "Editor" / "Data" / "Managed" / "UnityEngine").mkdir(parents=True)
    project = tmp_path / "Project"
    script_assemblies = project / "Library" / "ScriptAssemblies"
    script_assemblies.mkdir(parents=True)
    for assembly in fixture_assemblies.values():
        shutil.copy2(assembly, script_assemblies / assembly.name)

    project_feature = project / "Assets" / "ProjectFeature"
    project_feature.mkdir(parents=True)
    (project_feature / "PublicSurface.asmdef").write_text(
        json.dumps(
            {
                "name": "PublicSurface",
                "includePlatforms": ["Editor"],
                "defineConstraints": ["FEATURE_ENABLED"],
            }
        ),
        encoding="utf-8",
    )
    (project_feature / "Feature.cs").write_text("// fixture", encoding="utf-8")

    test_feature = project / "Assets" / "Tests"
    test_feature.mkdir(parents=True)
    (test_feature / "TestSurface.asmdef").write_text(
        json.dumps(
            {
                "name": "TestSurface",
                "optionalUnityReferences": ["TestAssemblies"],
            }
        ),
        encoding="utf-8",
    )
    (test_feature / "Tests.cs").write_text("// fixture", encoding="utf-8")

    embedded = project / "Packages" / "com.example.embedded"
    embedded.mkdir(parents=True)
    (embedded / "package.json").write_text(
        json.dumps({"name": "com.example.embedded", "version": "0.5.0"}),
        encoding="utf-8",
    )
    (embedded / "ForwardTarget.asmdef").write_text(
        json.dumps({"name": "ForwardTarget", "excludePlatforms": ["WebGL"]}),
        encoding="utf-8",
    )
    (embedded / "Runtime.cs").write_text("// fixture", encoding="utf-8")

    registry = project / "Library" / "PackageCache" / "com.example.registry@1.2.3"
    registry.mkdir(parents=True)
    (registry / "package.json").write_text(
        json.dumps({"name": "com.example.registry", "version": "1.2.3"}),
        encoding="utf-8",
    )
    (registry / "RegistrySurface.asmdef").write_text(
        json.dumps({"name": "RegistrySurface", "autoReferenced": False}),
        encoding="utf-8",
    )
    (registry / "Registry.cs").write_text("// fixture", encoding="utf-8")

    packages = project / "Packages"
    (packages / "manifest.json").write_text(
        json.dumps(
            {
                "dependencies": {
                    "com.example.embedded": "file:com.example.embedded",
                    "com.example.registry": "1.2.3",
                }
            }
        ),
        encoding="utf-8",
    )
    (packages / "packages-lock.json").write_text(
        json.dumps(
            {
                "dependencies": {
                    "com.example.embedded": {
                        "version": "file:com.example.embedded",
                        "depth": 0,
                        "source": "embedded",
                        "dependencies": {},
                    },
                    "com.example.registry": {
                        "version": "1.2.3",
                        "depth": 0,
                        "source": "registry",
                        "url": "https://packages.unity.com",
                        "dependencies": {},
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    snapshot = tmp_path / "project.jsonl"
    summary_path = tmp_path / "project-summary.json"

    # Act
    result = _run_tool(
        inventory_tool,
        "inventory",
        "--unity-root",
        str(unity_root),
        "--unity-version",
        "6000.5.1f1",
        "--unity-revision",
        "abc123",
        "--capture-time",
        FIXED_CAPTURE_TIME,
        "--build-target",
        "StandaloneWindows64",
        "--api-compatibility",
        "NET_Standard_2_1",
        "--project-root",
        str(project),
        "--assembly-root",
        str(script_assemblies),
        "--output",
        str(snapshot),
        "--summary",
        str(summary_path),
    )

    # Assert
    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assemblies = {item["name"]: item for item in summary["assemblies"]}
    project_provenance = assemblies["PublicSurface"]["provenance"]
    assert project_provenance["classification"] == "project"
    assert project_provenance["asmdef"] == "Assets/ProjectFeature/PublicSurface.asmdef"
    assert project_provenance["source_root"] == "Assets/ProjectFeature"
    assert project_provenance["source_file_count"] == 1
    assert project_provenance["variant_evidence"] == {
        "include_platforms": ["Editor"],
        "exclude_platforms": [],
        "define_constraints": ["FEATURE_ENABLED"],
        "optional_unity_references": [],
        "auto_referenced": True,
    }

    test_provenance = assemblies["TestSurface"]["provenance"]
    assert test_provenance["classification"] == "test"
    assert test_provenance["variant_evidence"]["optional_unity_references"] == ["TestAssemblies"]

    embedded_provenance = assemblies["ForwardTarget"]["provenance"]
    assert embedded_provenance["classification"] == "package"
    assert embedded_provenance["package_id"] == "com.example.embedded"
    assert embedded_provenance["package_version"] == "0.5.0"
    assert embedded_provenance["package_source"] == "embedded"
    assert embedded_provenance["manifest_path"] == ("Packages/com.example.embedded/package.json")

    registry_provenance = assemblies["RegistrySurface"]["provenance"]
    assert registry_provenance["classification"] == "package"
    assert registry_provenance["package_id"] == "com.example.registry"
    assert registry_provenance["package_version"] == "1.2.3"
    assert registry_provenance["package_source"] == "registry"
    assert registry_provenance["package_lock_path"] == "Packages/packages-lock.json"

    assert summary["project_metadata"]["status"] == "joined"
    assert summary["project_metadata"]["asmdef_count"] == 4
    assert summary["project_metadata"]["matched_assembly_count"] == 4
    assert summary["project_metadata"]["unresolved_assembly_names"] == []
    source_maps = {
        item["assembly_name"]: item for item in summary["project_metadata"]["source_maps"]
    }
    assert source_maps["PublicSurface"] == {
        "assembly_name": "PublicSurface",
        "asmdef": "Assets/ProjectFeature/PublicSurface.asmdef",
        "source_files": ["Assets/ProjectFeature/Feature.cs"],
    }
    assert source_maps["ForwardTarget"]["source_files"] == [
        "Packages/com.example.embedded/Runtime.cs"
    ]
    assert source_maps["RegistrySurface"]["source_files"] == [
        "Library/PackageCache/com.example.registry@1.2.3/Registry.cs"
    ]


def test_registry_build_classifies_every_symbol_without_false_generic_claims(
    inventory_tool: Path,
    tmp_path: Path,
) -> None:
    # Arrange
    snapshot = tmp_path / "snapshot.jsonl"
    summary = tmp_path / "summary.json"
    overrides = tmp_path / "overrides.json"
    first_registry = tmp_path / "registry.json"
    second_registry = tmp_path / "registry-again.json"
    records = [
        _record("Assembly::Typed"),
        _record("Assembly::Unwrapped"),
        _record("Assembly::Old", obsolete=True),
    ]
    _write_jsonl(snapshot, records)
    snapshot_hash = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    summary.write_text(
        json.dumps({"snapshot_sha256": snapshot_hash, "unity": {"version": "6000.5.1f1"}}),
        encoding="utf-8",
    )
    overrides.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "records": [
                    {
                        "symbol_id": "Assembly::Typed",
                        "classification": "typed",
                        "rationale": "Verified fixture command contract",
                        "proof": ["python_contract:test_fixture", "csharp_compile:test_fixture"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    # Act
    common = (
        "registry-build",
        "--snapshot",
        str(snapshot),
        "--summary",
        str(summary),
        "--overrides",
        str(overrides),
    )
    first = _run_tool(inventory_tool, *common, "--output", str(first_registry))
    second = _run_tool(inventory_tool, *common, "--output", str(second_registry))
    gate = _run_tool(
        inventory_tool,
        "coverage-gate",
        "--snapshot",
        str(snapshot),
        "--registry",
        str(first_registry),
        "--output",
        str(tmp_path / "gate.json"),
    )

    # Assert
    assert first.returncode == 0, first.stdout + first.stderr
    assert second.returncode == 0, second.stdout + second.stderr
    assert gate.returncode == 0, gate.stdout + gate.stderr
    assert first_registry.read_bytes() == second_registry.read_bytes()
    registry = json.loads(first_registry.read_text(encoding="utf-8"))
    assert registry["snapshot"] == {
        "sha256": snapshot_hash,
        "unity_version": "6000.5.1f1",
    }
    classifications = {
        record["symbol_id"]: record["classification"] for record in registry["records"]
    }
    assert classifications == {
        "Assembly::Old": "obsolete",
        "Assembly::Typed": "typed",
        "Assembly::Unwrapped": "public_unwrapped",
    }

    overrides_data = json.loads(overrides.read_text(encoding="utf-8"))
    overrides_data["records"][0]["classification"] = "generic"
    overrides.write_text(json.dumps(overrides_data), encoding="utf-8")
    rejected = _run_tool(inventory_tool, *common, "--output", str(tmp_path / "invalid.json"))
    assert rejected.returncode == 2
    assert (
        "generic classification requires csharp_compile and live_positive proof" in rejected.stderr
    )


def test_registry_build_promotes_only_exact_live_proven_assemblies(
    inventory_tool: Path,
    tmp_path: Path,
) -> None:
    # Arrange
    snapshot = tmp_path / "snapshot.jsonl"
    summary = tmp_path / "summary.json"
    proof_path = tmp_path / "generic-proof.json"
    registry_path = tmp_path / "registry.json"
    proven = {
        "name": "UnityEditor.CoreModule",
        "path": "Editor/Data/Managed/UnityEngine/UnityEditor.CoreModule.dll",
        "mvid": "11111111-1111-1111-1111-111111111111",
        "sha256": "a" * 64,
    }
    unproven = {
        "name": "UnityEditor.GIModule",
        "path": "Editor/Data/Managed/UnityEngine/UnityEditor.GIModule.dll",
        "mvid": "22222222-2222-2222-2222-222222222222",
        "sha256": "b" * 64,
    }
    _write_jsonl(
        snapshot,
        [
            _record("Core::Current", assembly=proven),
            _record("Core::Old", obsolete=True, assembly=proven),
            _record("GI::Current", assembly=unproven),
        ],
    )
    snapshot_hash = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    summary.write_text(
        json.dumps({"snapshot_sha256": snapshot_hash, "unity": {"version": "6000.5.1f1"}}),
        encoding="utf-8",
    )
    proof_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "snapshot": {
                    "sha256": snapshot_hash,
                    "unity_version": "6000.5.1f1",
                },
                "assemblies": [
                    {
                        **proven,
                        "proof": [
                            "csharp_compile:exact_identity_probe",
                            "live_positive:unity_6000_5_fixture",
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    # Act
    result = _run_tool(
        inventory_tool,
        "registry-build",
        "--snapshot",
        str(snapshot),
        "--summary",
        str(summary),
        "--generic-proof",
        str(proof_path),
        "--output",
        str(registry_path),
    )

    # Assert
    assert result.returncode == 0, result.stdout + result.stderr
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    classifications = {
        record["symbol_id"]: record["classification"] for record in registry["records"]
    }
    assert classifications == {
        "Core::Current": "generic",
        "Core::Old": "obsolete",
        "GI::Current": "public_unwrapped",
    }
    generic = next(
        record for record in registry["records"] if record["symbol_id"] == "Core::Current"
    )
    assert generic["proof"] == [
        "csharp_compile:exact_identity_probe",
        "live_positive:unity_6000_5_fixture",
    ]

    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    proof["snapshot"]["sha256"] = "f" * 64
    proof_path.write_text(json.dumps(proof), encoding="utf-8")
    rejected = _run_tool(
        inventory_tool,
        "registry-build",
        "--snapshot",
        str(snapshot),
        "--summary",
        str(summary),
        "--generic-proof",
        str(proof_path),
        "--output",
        str(tmp_path / "rejected.json"),
    )
    assert rejected.returncode == 2
    assert "must match the supplied summary" in rejected.stderr

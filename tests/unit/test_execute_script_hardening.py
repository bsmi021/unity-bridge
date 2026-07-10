"""Source and executable contract tests for the hardened generic script host."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
BRIDGE_DIR = ROOT / "ClaudeCodeBridge"


@pytest.fixture(scope="module")
def generic_host_core_harness(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _build_harness(
        tmp_path_factory.mktemp("generic-host-core"),
        "GenericHostCoreHarness",
        [
            "ExecuteScriptModels.cs",
            "ExecuteScriptAssemblyResolver.cs",
            "ExecuteScriptManifestValidator.cs",
            "ExecuteScriptReflectionPolicy.cs",
            "ExecuteScriptDiagnostics.cs",
        ],
        _core_harness_program(),
    )


@pytest.fixture(scope="module")
def generic_host_serializer_harness(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _build_harness(
        tmp_path_factory.mktemp("generic-host-serializer"),
        "GenericHostSerializerHarness",
        ["ExecuteScriptModels.cs", "ExecuteScriptResultSerializer.cs"],
        _serializer_harness_program(),
    )


@pytest.mark.parametrize(
    "mode",
    [
        "references",
        "ambiguous-reference",
        "exact-reference",
        "facade-rejected",
        "missing-reference",
        "manifest",
        "reflection-gate",
        "diagnostics",
    ],
)
def test_core_generic_host_policies_are_executable(
    generic_host_core_harness: Path, mode: str
) -> None:
    # Arrange / Act
    completed = _run_harness(generic_host_core_harness, mode)

    # Assert
    assert completed.returncode == 0, completed.stdout + completed.stderr


@pytest.mark.parametrize(
    "mode",
    [
        "primitive",
        "enum",
        "collection",
        "dictionary",
        "unity-object",
        "dto",
        "unsupported",
        "schema-mismatch",
    ],
)
def test_structured_result_serialization_is_executable(
    generic_host_serializer_harness: Path, mode: str
) -> None:
    # Arrange / Act
    completed = _run_harness(generic_host_serializer_harness, mode)

    # Assert
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_handler_composes_hardened_host_services() -> None:
    # Arrange
    handler_source = (BRIDGE_DIR / "ExecuteScriptCommandHandler.cs").read_text(encoding="utf-8")

    # Act / Assert
    assert "ExecuteScriptManifestValidator.Validate" in handler_source
    assert "ExecuteScriptAssemblyResolver.Resolve" in handler_source
    assert "ExecuteScriptReflectionPolicy.Validate" in handler_source
    assert "ExecuteScriptResultSerializer.TrySerialize" in handler_source
    assert "ExecuteScriptLogCapture" in handler_source
    assert "ExecuteScriptMutationScope" in handler_source
    assert "compilerDiagnostics" in handler_source
    assert "unityLogs" in handler_source
    assert "resolvedAssemblies = outcome.ResolvedAssemblies" in handler_source
    assert "assemblyResolutionIssues = outcome.AssemblyResolutionIssues" in handler_source
    assert "response.dataJson" in handler_source
    assert "result = value?.ToString()" not in handler_source
    assert "typeof(Enumerable).Assembly.GetName().Name" not in handler_source
    assert "ExecuteScriptDiagnostics.HasErrors" in handler_source


def test_unity_only_governance_uses_public_editor_contracts() -> None:
    # Arrange
    mutation_source = (BRIDGE_DIR / "ExecuteScriptMutationScope.cs").read_text(encoding="utf-8")
    log_source = (BRIDGE_DIR / "ExecuteScriptLogCapture.cs").read_text(encoding="utf-8")

    # Act / Assert
    assert "Undo.IncrementCurrentGroup" in mutation_source
    assert "Undo.SetCurrentGroupName" in mutation_source
    assert "Undo.postprocessModifications" in mutation_source
    assert "Undo.CollapseUndoOperations" in mutation_source
    assert "Undo.RevertAllDownToGroup" in mutation_source
    assert "Application.dataPath" in mutation_source
    assert "GlobalObjectId.GetGlobalObjectIdSlow" in mutation_source
    assert "GetEntityId" in mutation_source
    assert "UNITY_6000_5_OR_NEWER" in mutation_source
    assert "Application.logMessageReceived +=" in log_source
    assert "Application.logMessageReceived -=" in log_source


def test_new_execute_script_sources_have_paired_meta_files() -> None:
    # Arrange
    sources = sorted(BRIDGE_DIR.glob("ExecuteScript*.cs"))

    # Act
    missing = [source.name for source in sources if not Path(f"{source}.meta").is_file()]

    # Assert
    assert sources
    assert missing == []


def _build_harness(
    project_dir: Path,
    assembly_name: str,
    bridge_sources: list[str],
    program: str,
) -> Path:
    # Arrange
    project_file = project_dir / f"{assembly_name}.csproj"
    compile_items = "\n".join(
        f'    <Compile Include="{(BRIDGE_DIR / source).as_posix()}" Link="{source}" />'
        for source in bridge_sources
    )
    project_file.write_text(
        f"""<Project Sdk=\"Microsoft.NET.Sdk\">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <AssemblyName>{assembly_name}</AssemblyName>
    <ImplicitUsings>disable</ImplicitUsings>
    <Nullable>disable</Nullable>
  </PropertyGroup>
  <ItemGroup>
{compile_items}
  </ItemGroup>
</Project>
""",
        encoding="utf-8",
    )
    (project_dir / "Program.cs").write_text(program, encoding="utf-8")

    # Act
    completed = subprocess.run(
        ["dotnet", "build", str(project_file), "--nologo", "--verbosity", "quiet"],
        check=False,
        capture_output=True,
        text=True,
        env=_dotnet_environment(),
    )

    # Assert
    assert completed.returncode == 0, completed.stdout + completed.stderr
    harness = project_dir / "bin" / "Debug" / "net8.0" / f"{assembly_name}.dll"
    assert harness.is_file()
    return harness


def _run_harness(harness: Path, mode: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["dotnet", str(harness), mode],
        check=False,
        capture_output=True,
        text=True,
        env=_dotnet_environment(),
    )


def _dotnet_environment() -> dict[str, str]:
    return {
        **os.environ,
        "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
        "DOTNET_NOLOGO": "1",
    }


def _core_harness_program() -> str:
    return r"""using System;
using System.Collections.Generic;
using System.Linq;
using BWS.Editor.ClaudeCodeBridge;

internal static class Program
{
    private static int Main(string[] args)
    {
        try
        {
            switch (args[0])
            {
                case "references": return References();
                case "ambiguous-reference": return AmbiguousReference();
                case "exact-reference": return ExactReference();
                case "facade-rejected": return FacadeRejected();
                case "missing-reference": return MissingReference();
                case "manifest": return Manifest();
                case "reflection-gate": return ReflectionGate();
                case "diagnostics": return Diagnostics();
                default: return 2;
            }
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(ex);
            return 1;
        }
    }

    private static int References()
    {
        var candidates = new[]
        {
            new ExecuteScriptAssemblyCandidate("UnityEngine.CoreModule", "z.dll", false, false),
            new ExecuteScriptAssemblyCandidate("System.Core", "system-core.dll", false, false),
            new ExecuteScriptAssemblyCandidate("UnityEditor.CoreModule", "editor.dll", false, false),
            new ExecuteScriptAssemblyCandidate("netstandard", "facade.dll", false, true),
            new ExecuteScriptAssemblyCandidate("Dynamic.Project", "", true, false),
        };
        var requested = new[]
        {
            "UnityEngine.CoreModule", "System.Core", "UnityEditor.CoreModule"
        };
        var selected = ExecuteScriptAssemblyResolver.SelectCandidates(
            candidates, requested, out var error);
        var names = string.Join(",", selected.Select(candidate => candidate.Name));
        return error == ""
            && names == "System.Core,UnityEditor.CoreModule,UnityEngine.CoreModule" ? 0 : 1;
    }

    private static int AmbiguousReference()
    {
        var firstPath = System.IO.Path.GetFullPath("packages/a/Duplicate.Editor.dll");
        var secondPath = System.IO.Path.GetFullPath("packages/b/Duplicate.Editor.dll");
        var candidates = new[]
        {
            new ExecuteScriptAssemblyCandidate(
                "Duplicate.Editor", firstPath,
                "Duplicate.Editor, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null",
                "11111111-1111-1111-1111-111111111111", false, false),
            new ExecuteScriptAssemblyCandidate(
                "Duplicate.Editor", secondPath,
                "Duplicate.Editor, Version=2.0.0.0, Culture=neutral, PublicKeyToken=null",
                "22222222-2222-2222-2222-222222222222", false, false),
        };
        var requests = new[] { new ExecuteScriptAssemblyRequest { name = "Duplicate.Editor" } };

        var selected = ExecuteScriptAssemblyResolver.SelectCandidates(
            candidates, requests, out var issue);

        return selected.Count == 0
            && issue.code == "ambiguous_simple_name"
            && issue.request.name == "Duplicate.Editor"
            && issue.candidates.Count == 2
            && issue.candidates[0].fullName.Contains("Version=1.0.0.0")
            && issue.candidates[1].fullName.Contains("Version=2.0.0.0")
            && issue.candidates.All(candidate => candidate.mvid.Length == 36)
            && issue.candidates.All(candidate => System.IO.Path.IsPathFullyQualified(candidate.path))
            ? 0 : 1;
    }

    private static int ExactReference()
    {
        var firstPath = System.IO.Path.GetFullPath("packages/a/Duplicate.Editor.dll");
        var secondPath = System.IO.Path.GetFullPath("packages/b/Duplicate.Editor.dll");
        var candidates = new[]
        {
            new ExecuteScriptAssemblyCandidate(
                "Duplicate.Editor", firstPath,
                "Duplicate.Editor, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null",
                "11111111-1111-1111-1111-111111111111", false, false),
            new ExecuteScriptAssemblyCandidate(
                "Duplicate.Editor", secondPath,
                "Duplicate.Editor, Version=2.0.0.0, Culture=neutral, PublicKeyToken=null",
                "22222222-2222-2222-2222-222222222222", false, false),
        };
        var requests = new[]
        {
            new ExecuteScriptAssemblyRequest
            {
                fullName = "Duplicate.Editor, Version=2.0.0.0, Culture=neutral, PublicKeyToken=null",
                mvid = "22222222-2222-2222-2222-222222222222",
                path = System.IO.Path.Combine(secondPath, "..", "Duplicate.Editor.dll"),
            },
        };

        var selected = ExecuteScriptAssemblyResolver.SelectCandidates(
            candidates, requests, out var issue);
        var identity = selected.Single().Identity;

        return issue == null
            && identity.fullName.Contains("Version=2.0.0.0")
            && identity.mvid == "22222222-2222-2222-2222-222222222222"
            && identity.path == secondPath.Replace('\\', '/')
            ? 0 : 1;
    }

    private static int MissingReference()
    {
        var selected = ExecuteScriptAssemblyResolver.SelectCandidates(
            new[] { new ExecuteScriptAssemblyCandidate("System.Core", "core.dll", false, false) },
            new[] { "Missing.Editor" },
            out var error);
        return selected.Count == 0 && error.Contains("Missing.Editor") ? 0 : 1;
    }

    private static int FacadeRejected()
    {
        var selected = ExecuteScriptAssemblyResolver.SelectCandidates(
            new[] { new ExecuteScriptAssemblyCandidate("netstandard", "facade.dll", false, true) },
            new[] { "netstandard" },
            out var error);
        return selected.Count == 0 && error.Contains("safely referenceable") ? 0 : 1;
    }

    private static int Manifest()
    {
        var valid = new ExecuteScriptManifest
        {
            intent = "mutating",
            expectedAssemblies = new List<string> { "Assembly-CSharp-Editor" },
            timeoutMs = 5000,
            undoLabel = "Mutation",
            declaredFilePaths = new List<string> { "Assets/Test.asset" },
            returnSchema = "dto",
        };
        var duplicate = new ExecuteScriptManifest
        {
            expectedAssemblies = new List<string> { "A", "A" },
        };
        var exact = new ExecuteScriptManifest
        {
            expectedAssemblyIdentities = new List<ExecuteScriptAssemblyRequest>
            {
                new ExecuteScriptAssemblyRequest
                {
                    fullName = "Package.Editor, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null",
                    mvid = "11111111-1111-1111-1111-111111111111",
                    path = System.IO.Path.GetFullPath("Package.Editor.dll"),
                },
            },
        };
        var invalidExact = new ExecuteScriptManifest
        {
            expectedAssemblyIdentities = new List<ExecuteScriptAssemblyRequest>
            {
                new ExecuteScriptAssemblyRequest
                {
                    fullName = "Package.Editor, Version=1.0.0.0",
                    mvid = "not-a-guid",
                    path = "Package.Editor.dll",
                },
            },
        };
        return ExecuteScriptManifestValidator.Validate(valid, out _)
            && !ExecuteScriptManifestValidator.Validate(duplicate, out var duplicateError)
            && duplicateError.Contains("duplicate")
            && ExecuteScriptManifestValidator.Validate(exact, out _)
            && exact.expectedAssemblyIdentities[0].path.Contains("/")
            && !ExecuteScriptManifestValidator.Validate(invalidExact, out var identityError)
            && identityError.Contains("MVID") ? 0 : 1;
    }

    private static int ReflectionGate()
    {
        const string code = "typeof(Foo).GetFields(BindingFlags.NonPublic);";
        return !ExecuteScriptReflectionPolicy.Validate(code, false, out var blocked)
            && blocked.Contains("allowInternalReflection")
            && ExecuteScriptReflectionPolicy.Validate(code, true, out _) ? 0 : 1;
    }

    private static int Diagnostics()
    {
        const string report = "input.cs(1,2): error CS1002: ; expected\nwarning CS0219: assigned";
        var diagnostics = ExecuteScriptDiagnostics.Parse(report);
        return diagnostics.Count == 2
            && diagnostics[0].severity == "error"
            && diagnostics[0].code == "CS1002"
            && diagnostics[1].severity == "warning"
            && ExecuteScriptDiagnostics.HasErrors(diagnostics) ? 0 : 1;
    }
}
"""


def _serializer_harness_program() -> str:
    return r"""using System;
using System.Collections.Generic;
using System.Linq;
using BWS.Editor.ClaudeCodeBridge;

namespace UnityEngine
{
    public class Object
    {
        public string name = "TestObject";
        public int GetInstanceID() => 17;
    }
}

namespace UnityEditor
{
    public static class AssetDatabase
    {
        public static string GetAssetPath(UnityEngine.Object value) => "Assets/Test.asset";
    }

    public struct GlobalObjectId
    {
        public static GlobalObjectId GetGlobalObjectIdSlow(UnityEngine.Object value) =>
            new GlobalObjectId();
        public override string ToString() => "GlobalObjectId_V1-Test";
    }
}

internal enum SampleEnum { First, Second }

[Serializable]
internal sealed class SampleDto
{
    public int count = 3;
    public string name = "sample";
}

internal sealed class UnsupportedValue
{
    public int Value { get; set; } = 4;
}

internal static class Program
{
    private static int Main(string[] args)
    {
        try
        {
            switch (args[0])
            {
                case "primitive": return Primitive();
                case "enum": return EnumValue();
                case "collection": return Collection();
                case "dictionary": return DictionaryValue();
                case "unity-object": return UnityObject();
                case "dto": return Dto();
                case "unsupported": return Unsupported();
                case "schema-mismatch": return SchemaMismatch();
                default: return 2;
            }
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(ex);
            return 1;
        }
    }

    private static int Primitive()
    {
        return Serialize(42, "auto", out var value, out _)
            && value.kind == "integer" && value.stringValue == "42" ? 0 : 1;
    }

    private static int EnumValue()
    {
        return Serialize(SampleEnum.Second, "auto", out var value, out _)
            && value.kind == "enum" && value.stringValue == "Second" ? 0 : 1;
    }

    private static int Collection()
    {
        return Serialize(new List<int> { 1, 2 }, "collection", out var value, out _)
            && value.kind == "collection" && value.items.Count == 2 ? 0 : 1;
    }

    private static int DictionaryValue()
    {
        var input = new Dictionary<string, int> { ["count"] = 2 };
        return Serialize(input, "dictionary", out var value, out _)
            && value.kind == "dictionary" && value.entries.Count == 1
            && value.entries[0].key.stringValue == "count" ? 0 : 1;
    }

    private static int UnityObject()
    {
        return Serialize(new UnityEngine.Object(), "unity-object", out var value, out _)
            && value.kind == "unity-object" && value.unityObject.objectId == "17"
            && value.unityObject.assetPath == "Assets/Test.asset" ? 0 : 1;
    }

    private static int Dto()
    {
        return Serialize(new SampleDto(), "dto", out var value, out _)
            && value.kind == "dto" && value.fields.Count == 2
            && value.fields.Select(field => field.name).SequenceEqual(new[] { "count", "name" })
            ? 0 : 1;
    }

    private static int Unsupported()
    {
        return !Serialize(new UnsupportedValue(), "auto", out _, out var error)
            && error.Contains("Unsupported result type") ? 0 : 1;
    }

    private static int SchemaMismatch()
    {
        return !Serialize(new[] { 1, 2 }, "scalar", out _, out var error)
            && error.Contains("return schema") ? 0 : 1;
    }

    private static bool Serialize(
        object input, string schema, out ExecuteScriptValue value, out string error) =>
        ExecuteScriptResultSerializer.TrySerialize(input, true, schema, out value, out error);
}
"""

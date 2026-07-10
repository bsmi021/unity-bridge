"""Executable contracts for declared generic-script mutation targets."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
BRIDGE_DIR = ROOT / "ClaudeCodeBridge"


@pytest.fixture(scope="module")
def mutation_harness(tmp_path_factory: pytest.TempPathFactory) -> Path:
    project_dir = tmp_path_factory.mktemp("execute-script-mutations")
    project_file = project_dir / "MutationHarness.csproj"
    sources = [
        "ExecuteScriptModels.cs",
        "ExecuteScriptAssemblyResolver.cs",
        "ExecuteScriptManifestValidator.cs",
        "ProjectAssetPath.cs",
        "AssetFileMutationScope.cs",
        "ExecuteScriptFileTransaction.cs",
        "ExecuteScriptMutationScope.cs",
    ]
    compile_items = "\n".join(
        f'    <Compile Include="{(BRIDGE_DIR / source).as_posix()}" Link="{source}" />'
        for source in sources
    )
    project_file.write_text(
        f"""<Project Sdk=\"Microsoft.NET.Sdk\">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <AssemblyName>MutationHarness</AssemblyName>
    <ImplicitUsings>disable</ImplicitUsings>
    <Nullable>disable</Nullable>
    <DefineConstants>UNITY_6000_5_OR_NEWER</DefineConstants>
  </PropertyGroup>
  <ItemGroup>
{compile_items}
  </ItemGroup>
</Project>
""",
        encoding="utf-8",
    )
    (project_dir / "Program.cs").write_text(_harness_program(), encoding="utf-8")

    completed = subprocess.run(
        ["dotnet", "build", str(project_file), "--nologo", "--verbosity", "quiet"],
        check=False,
        capture_output=True,
        text=True,
        env=_dotnet_environment(),
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    return project_dir / "bin" / "Debug" / "net8.0" / "MutationHarness.dll"


@pytest.mark.parametrize(
    "mode",
    [
        "requires-targets",
        "rejects-traversal",
        "rejects-reparse",
        "records-object",
        "restores-file-and-meta",
        "rejects-undeclared-file",
        "failed-verification-is-not-reverted",
    ],
)
def test_transactional_mutation_contracts_are_executable(mutation_harness: Path, mode: str) -> None:
    completed = subprocess.run(
        ["dotnet", str(mutation_harness), mode],
        check=False,
        capture_output=True,
        text=True,
        env=_dotnet_environment(),
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_handler_fails_closed_before_executing_mutating_code() -> None:
    source = (BRIDGE_DIR / "ExecuteScriptCommandHandler.cs").read_text(encoding="utf-8")

    begin_index = source.index("ExecuteScriptMutationScope.TryBegin")
    execute_index = source.index("ExecuteCode(parameters)")

    assert begin_index < execute_index
    assert "mutation.Complete(outcome.Success" in source


def _dotnet_environment() -> dict[str, str]:
    return {
        **os.environ,
        "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
        "DOTNET_NOLOGO": "1",
    }


def _harness_program() -> str:
    return r"""using System;
using System.Collections.Generic;
using System.IO;
using BWS.Editor.ClaudeCodeBridge;

namespace UnityEngine
{
    public class Object
    {
        public string name = "Object";
        public int state;
        public long GetEntityId() => 42;
        public static implicit operator bool(Object value) => value != null;
    }

    public static class Application
    {
        public static string dataPath;
    }
}

namespace UnityEditor
{
    public class PropertyModification { public UnityEngine.Object target; }
    public struct UndoPropertyModification
    {
        public PropertyModification currentValue;
        public PropertyModification previousValue;
    }

    public static class Undo
    {
        public delegate UndoPropertyModification[] PostprocessModifications(
            UndoPropertyModification[] modifications);
        public static event PostprocessModifications postprocessModifications;
        public static readonly List<UnityEngine.Object> Recorded = new List<UnityEngine.Object>();
        public static void IncrementCurrentGroup() { }
        public static int GetCurrentGroup() => 7;
        public static void SetCurrentGroupName(string label) { }
        public static void RegisterCompleteObjectUndo(UnityEngine.Object value, string label) =>
            Recorded.Add(value);
        public static void CollapseUndoOperations(int group) { }
        public static void RevertAllDownToGroup(int group) { }
    }

    public struct GlobalObjectId
    {
        private string _value;
        public static readonly Dictionary<string, UnityEngine.Object> Objects =
            new Dictionary<string, UnityEngine.Object>();
        public static bool TryParse(string value, out GlobalObjectId id)
        {
            id = new GlobalObjectId { _value = value };
            return value != null && value.StartsWith("GlobalObjectId_V1-");
        }
        public static UnityEngine.Object GlobalObjectIdentifierToObjectSlow(GlobalObjectId id) =>
            Objects.TryGetValue(id._value, out var value) ? value : null;
        public static GlobalObjectId GetGlobalObjectIdSlow(UnityEngine.Object value) =>
            new GlobalObjectId { _value = "GlobalObjectId_V1-known" };
        public override string ToString() => _value;
    }

    public static class AssetDatabase
    {
        public static string GetAssetPath(UnityEngine.Object value) => "Assets/Test.asset";
    }

    public static class EditorJsonUtility
    {
        public static string ToJson(UnityEngine.Object value) => value.state.ToString();
    }
}

internal static class Program
{
    private static string _root;
    private static int Main(string[] args)
    {
        _root = Path.Combine(Path.GetTempPath(), "unity-bridge-mutation-" + Guid.NewGuid());
        Directory.CreateDirectory(Path.Combine(_root, "Assets"));
        UnityEngine.Application.dataPath = Path.Combine(_root, "Assets");
        try
        {
            switch (args[0])
            {
                case "requires-targets": return RequiresTargets();
                case "rejects-traversal": return RejectsTraversal();
                case "rejects-reparse": return RejectsReparse();
                case "records-object": return RecordsObject();
                case "restores-file-and-meta": return RestoresFileAndMeta();
                case "rejects-undeclared-file": return RejectsUndeclaredFile();
                case "failed-verification-is-not-reverted": return FailedVerification();
                default: return 2;
            }
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(ex);
            return 1;
        }
        finally
        {
            try { Directory.Delete(_root, true); } catch { }
        }
    }

    private static ExecuteScriptManifest Manifest(
        IEnumerable<string> objects = null, IEnumerable<string> files = null) =>
        new ExecuteScriptManifest
        {
            intent = "mutating",
            undoLabel = "Test mutation",
            declaredObjectIds = new List<string>(objects ?? Array.Empty<string>()),
            declaredFilePaths = new List<string>(files ?? Array.Empty<string>()),
        };

    private static int RequiresTargets()
    {
        var valid = ExecuteScriptManifestValidator.Validate(Manifest(), out var error);
        return !valid && error.Contains("declared") ? 0 : 1;
    }

    private static int RejectsTraversal()
    {
        var manifest = Manifest(files: new[] { "Assets/../outside.asset" });
        return !ExecuteScriptMutationScope.TryBegin(manifest, out _, out var error)
            && error.Contains("Invalid asset path") ? 0 : 1;
    }

    private static int RejectsReparse()
    {
        var link = Path.Combine(UnityEngine.Application.dataPath, "linked");
        var outside = Path.Combine(_root, "outside");
        Directory.CreateDirectory(outside);
        try { Directory.CreateSymbolicLink(link, outside); }
        catch (Exception) { return 0; }
        var manifest = Manifest(files: new[] { "Assets/linked/config.asset" });
        return !ExecuteScriptMutationScope.TryBegin(manifest, out _, out var error)
            && error.Contains("Invalid asset path") ? 0 : 1;
    }

    private static int RecordsObject()
    {
        const string id = "GlobalObjectId_V1-known";
        var value = new UnityEngine.Object();
        UnityEditor.GlobalObjectId.Objects[id] = value;
        using (var scope = Begin(Manifest(objects: new[] { id })))
            return UnityEditor.Undo.Recorded.Contains(value) ? 0 : 1;
    }

    private static int RestoresFileAndMeta()
    {
        var fullPath = Path.Combine(UnityEngine.Application.dataPath, "config.asset");
        File.WriteAllText(fullPath, "before");
        File.WriteAllText(fullPath + ".meta", "meta-before");
        using (var scope = Begin(Manifest(files: new[] { "Assets/config.asset" })))
        {
            File.WriteAllText(fullPath, "after");
            File.WriteAllText(fullPath + ".meta", "meta-after");
            var accepted = scope.Complete(false, out _);
            return !accepted && scope.Report.reverted
                && File.ReadAllText(fullPath) == "before"
                && File.ReadAllText(fullPath + ".meta") == "meta-before" ? 0 : 1;
        }
    }

    private static int RejectsUndeclaredFile()
    {
        var declared = Path.Combine(UnityEngine.Application.dataPath, "declared.asset");
        File.WriteAllText(declared, "before");
        using (var scope = Begin(Manifest(files: new[] { "Assets/declared.asset" })))
        {
            File.WriteAllText(Path.Combine(UnityEngine.Application.dataPath, "other.asset"), "new");
            var accepted = scope.Complete(true, out var error);
            return !accepted && !scope.Report.reverted && error.Contains("undeclared") ? 0 : 1;
        }
    }

    private static int FailedVerification()
    {
        var fullPath = Path.Combine(UnityEngine.Application.dataPath, "config.asset");
        File.WriteAllText(fullPath, "before");
        using (var scope = Begin(Manifest(files: new[] { "Assets/config.asset" })))
        {
            File.Delete(fullPath);
            Directory.CreateDirectory(fullPath);
            var accepted = scope.Complete(false, out _);
            return !accepted && !scope.Report.reverted ? 0 : 1;
        }
    }

    private static ExecuteScriptMutationScope Begin(ExecuteScriptManifest manifest)
    {
        if (!ExecuteScriptMutationScope.TryBegin(manifest, out var scope, out var error))
            throw new InvalidOperationException(error);
        return scope;
    }
}
"""

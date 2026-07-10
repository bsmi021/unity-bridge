"""Executable and structural tests for Phase 0 asset path safety."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
BRIDGE_DIR = ROOT / "ClaudeCodeBridge"


@pytest.fixture(scope="module")
def path_safety_harness(tmp_path_factory: pytest.TempPathFactory) -> Path:
    # Arrange
    project_dir = tmp_path_factory.mktemp("path-safety-harness")
    project_file = project_dir / "PathSafetyHarness.csproj"
    program_file = project_dir / "Program.cs"
    project_file.write_text(_harness_project(), encoding="utf-8")
    program_file.write_text(_harness_program(), encoding="utf-8")

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
    harness = project_dir / "bin" / "Debug" / "net8.0" / "PathSafetyHarness.dll"
    assert harness.is_file()
    return harness


@pytest.mark.parametrize(
    ("asset_path", "expected_valid"),
    [
        ("Assets/Models/Tree.fbx", True),
        ("Assets/../ProjectSettings/ProjectSettings.asset", False),
        ("Assets/../../ProjectBackup/secret.txt", False),
        ("AssetsBackup/secret.txt", False),
        ("C:/escape/secret.txt", False),
        ("/escape/secret.txt", False),
        (r"\\server\share\secret.txt", False),
        (r"Assets\Scripts\Player.cs", False),
        ("Assets//Scripts/Player.cs", False),
        ("Assets/./Scripts/Player.cs", False),
        ("Assets/Bad:Name.cs", False),
        ("Assets/", False),
    ],
)
def test_project_asset_path_resolution_is_canonically_contained(
    path_safety_harness: Path,
    tmp_path: Path,
    asset_path: str,
    expected_valid: bool,
) -> None:
    # Arrange
    assets_dir = tmp_path / "Project" / "Assets"
    assets_dir.mkdir(parents=True)

    # Act
    completed = _run_harness(path_safety_harness, "path", str(assets_dir), asset_path)
    actual_valid, full_path, message = completed.stdout.strip().split("|", maxsplit=2)

    # Assert
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert (actual_valid == "True") is expected_valid
    if expected_valid:
        assert Path(full_path) == assets_dir / "Models" / "Tree.fbx"
        assert message == ""
    else:
        assert full_path == ""
        assert "Invalid asset path" in message


def test_asset_file_mutation_refuses_implicit_overwrite(
    path_safety_harness: Path, tmp_path: Path
) -> None:
    # Arrange / Act
    completed = _run_harness(path_safety_harness, "refuse-overwrite", str(tmp_path))

    # Assert
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_project_asset_path_rejects_symlink_escape(
    path_safety_harness: Path, tmp_path: Path
) -> None:
    # Arrange
    assets_dir = tmp_path / "Project" / "Assets"
    outside_dir = tmp_path / "Outside"
    assets_dir.mkdir(parents=True)
    outside_dir.mkdir()
    link = assets_dir / "LinkedOutside"
    try:
        link.symlink_to(outside_dir, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"Directory symlinks are unavailable: {exc}")

    # Act
    completed = _run_harness(
        path_safety_harness,
        "path",
        str(assets_dir),
        "Assets/LinkedOutside/escape.txt",
    )
    actual_valid, full_path, message = completed.stdout.strip().split("|", maxsplit=2)

    # Assert
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert actual_valid == "False"
    assert full_path == ""
    assert "Invalid asset path" in message


def test_asset_file_mutation_rolls_back_only_new_destination(
    path_safety_harness: Path, tmp_path: Path
) -> None:
    # Arrange / Act
    completed = _run_harness(path_safety_harness, "rollback-new", str(tmp_path))

    # Assert
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_asset_file_mutation_restores_preexisting_file_and_meta(
    path_safety_harness: Path, tmp_path: Path
) -> None:
    # Arrange / Act
    completed = _run_harness(path_safety_harness, "rollback-existing", str(tmp_path))

    # Assert
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_asset_file_mutation_commits_explicit_overwrite(
    path_safety_harness: Path, tmp_path: Path
) -> None:
    # Arrange / Act
    completed = _run_harness(path_safety_harness, "commit-overwrite", str(tmp_path))

    # Assert
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_model_import_uses_explicit_overwrite_and_shared_rollback() -> None:
    # Arrange
    helper_source = (BRIDGE_DIR / "AssetExtendedHelpers.cs").read_text(encoding="utf-8")
    model_source = (BRIDGE_DIR / "AssetExtendedModels.cs").read_text(encoding="utf-8")

    # Act
    model_import_source = helper_source[
        helper_source.index("ExecuteImportModel") : helper_source.index("IsSupportedModelExtension")
    ]

    # Assert
    assert "ProjectAssetPath.TryResolve" in model_import_source
    assert "AssetFileMutationScope.TryBegin" in model_import_source
    assert "RollbackModelImport" in model_import_source
    assert "parameters.overwrite" in model_import_source
    assert "public bool overwrite = false;" in model_source


def test_asset_hash_uses_shared_canonical_path_resolution() -> None:
    # Arrange
    helper_source = (BRIDGE_DIR / "AssetExtendedHelpers.cs").read_text(encoding="utf-8")

    # Act
    hash_source = helper_source[
        helper_source.index("ExecuteHash") : helper_source.index("ComputeSha256")
    ]

    # Assert
    assert "ProjectAssetPath.TryResolve" in hash_source
    assert 'StartsWith("Assets/"' not in hash_source


def test_script_edit_uses_backup_commit_and_rollback_transaction() -> None:
    # Arrange
    source = (BRIDGE_DIR / "ScriptEditCommandHandler.cs").read_text(encoding="utf-8")

    # Act
    edit_source = source[
        source.index("private ScriptEditResult ExecuteEdit") : source.index(
            "private static bool TryResolveScriptPath"
        )
    ]

    # Assert
    assert "AssetFileMutationScope.TryBegin" in edit_source
    assert "ApplyScriptEditTransaction" in edit_source
    assert "mutation.Commit()" in edit_source
    assert "mutation.Rollback()" in edit_source


def _run_harness(harness: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["dotnet", str(harness), *arguments],
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


def _harness_project() -> str:
    path_source = (BRIDGE_DIR / "ProjectAssetPath.cs").as_posix()
    mutation_source = (BRIDGE_DIR / "AssetFileMutationScope.cs").as_posix()
    return f"""<Project Sdk=\"Microsoft.NET.Sdk\">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>disable</ImplicitUsings>
    <Nullable>disable</Nullable>
  </PropertyGroup>
  <ItemGroup>
    <Compile Include=\"{path_source}\" Link=\"ProjectAssetPath.cs\" />
    <Compile Include=\"{mutation_source}\" Link=\"AssetFileMutationScope.cs\" />
  </ItemGroup>
</Project>
"""


def _harness_program() -> str:
    return r"""using System;
using System.IO;
using BWS.Editor.ClaudeCodeBridge;

internal static class Program
{
    private static int Main(string[] args)
    {
        try
        {
            switch (args[0])
            {
                case "path":
                    return ResolvePath(args[1], args[2]);
                case "refuse-overwrite":
                    return RefuseOverwrite(args[1]);
                case "rollback-new":
                    return RollbackNew(args[1]);
                case "rollback-existing":
                    return RollbackExisting(args[1]);
                case "commit-overwrite":
                    return CommitOverwrite(args[1]);
                default:
                    return 2;
            }
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(ex);
            return 1;
        }
    }

    private static int ResolvePath(string assetsDirectory, string assetPath)
    {
        var valid = ProjectAssetPath.TryResolve(
            assetsDirectory, assetPath, out var fullPath, out var message);
        Console.WriteLine($"{valid}|{fullPath}|{message}");
        return 0;
    }

    private static int RefuseOverwrite(string directory)
    {
        var destination = PrepareFiles(directory, out _, out _);
        var started = AssetFileMutationScope.TryBegin(
            destination, false, out var mutation, out _);
        mutation?.Dispose();
        return !started && File.ReadAllText(destination) == "old" ? 0 : 1;
    }

    private static int RollbackNew(string directory)
    {
        Directory.CreateDirectory(directory);
        var source = Path.Combine(directory, "source.fbx");
        var destination = Path.Combine(directory, "new.fbx");
        File.WriteAllText(source, "new");
        using (var mutation = Begin(destination, false))
        {
            mutation.CopyFrom(source);
            File.WriteAllText(destination + ".meta", "generated-meta");
        }
        return !File.Exists(destination) && !File.Exists(destination + ".meta") ? 0 : 1;
    }

    private static int RollbackExisting(string directory)
    {
        var destination = PrepareFiles(directory, out var source, out var metadata);
        using (var mutation = Begin(destination, true))
        {
            mutation.CopyFrom(source);
            File.WriteAllText(metadata, "new-meta");
        }
        return File.ReadAllText(destination) == "old"
            && File.ReadAllText(metadata) == "old-meta" ? 0 : 1;
    }

    private static int CommitOverwrite(string directory)
    {
        var destination = PrepareFiles(directory, out var source, out var metadata);
        using (var mutation = Begin(destination, true))
        {
            mutation.CopyFrom(source);
            File.WriteAllText(metadata, "new-meta");
            mutation.Commit();
        }
        return File.ReadAllText(destination) == "new"
            && File.ReadAllText(metadata) == "new-meta" ? 0 : 1;
    }

    private static string PrepareFiles(
        string directory, out string source, out string metadata)
    {
        Directory.CreateDirectory(directory);
        source = Path.Combine(directory, "source.fbx");
        var destination = Path.Combine(directory, "destination.fbx");
        metadata = destination + ".meta";
        File.WriteAllText(source, "new");
        File.WriteAllText(destination, "old");
        File.WriteAllText(metadata, "old-meta");
        return destination;
    }

    private static AssetFileMutationScope Begin(string destination, bool overwrite)
    {
        if (!AssetFileMutationScope.TryBegin(
            destination, overwrite, out var mutation, out var message))
        {
            throw new InvalidOperationException(message);
        }
        return mutation;
    }
}
"""

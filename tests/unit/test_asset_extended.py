"""Unit tests for commands/asset_extended.py — all 10 asset extended operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from unity_bridge.app import app
from unity_bridge.commands.asset_extended import asset_extended_operation
from unity_bridge.core.bridge import CommandResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_parameters(call_args: Any) -> dict:
    """Extract the 'parameters' kwarg from a mock call."""
    if call_args.kwargs.get("parameters") is not None:
        return call_args.kwargs["parameters"]
    if len(call_args.args) >= 2:
        return call_args.args[1]
    return {}


def _extract_command_type(call_args: Any) -> str:
    if "command_type" in call_args.kwargs:
        return call_args.kwargs["command_type"]
    return call_args.args[0]


def _extract_kwarg(call_args: Any, key: str) -> Any:
    if key in call_args.kwargs:
        return call_args.kwargs[key]
    return None


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestAssetCreate:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(
            mock_bridge, "create", asset_path="Assets/Data/Cfg.asset", asset_type="ScriptableObject"
        )
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "asset-extended-operation"

    async def test_includes_asset_path_and_type(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(
            mock_bridge, "create", asset_path="Assets/Data/Cfg.asset", asset_type="Material"
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "create"
        assert params["assetPath"] == "Assets/Data/Cfg.asset"
        assert params["assetType"] == "Material"

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        expected = CommandResult(success=True, data={"operation": "create"})
        mock_bridge.send_command_with_retry.return_value = expected
        result = await asset_extended_operation(
            mock_bridge, "create", asset_path="Assets/X.asset", asset_type="Material"
        )
        assert result.success is True


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestAssetDelete:
    async def test_sends_delete_operation(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(mock_bridge, "delete", asset_path="Assets/Old.asset")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "delete"
        assert params["assetPath"] == "Assets/Old.asset"

    async def test_use_trash_flag_included(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(
            mock_bridge, "delete", asset_path="Assets/Old.asset", use_trash=True
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["useTrash"] is True

    async def test_use_trash_flag_omitted_when_false(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(
            mock_bridge, "delete", asset_path="Assets/Old.asset", use_trash=False
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "useTrash" not in params


# ---------------------------------------------------------------------------
# copy
# ---------------------------------------------------------------------------


class TestAssetCopy:
    async def test_sends_copy_with_paths(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(
            mock_bridge,
            "copy",
            source_path="Assets/A.prefab",
            destination_path="Assets/B.prefab",
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "copy"
        assert params["sourcePath"] == "Assets/A.prefab"
        assert params["destinationPath"] == "Assets/B.prefab"


# ---------------------------------------------------------------------------
# move
# ---------------------------------------------------------------------------


class TestAssetMove:
    async def test_sends_move_with_paths(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(
            mock_bridge,
            "move",
            source_path="Assets/Prefabs/Enemy.prefab",
            destination_path="Assets/Prefabs/Enemies/Enemy.prefab",
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "move"
        assert params["sourcePath"] == "Assets/Prefabs/Enemy.prefab"
        assert params["destinationPath"] == "Assets/Prefabs/Enemies/Enemy.prefab"


# ---------------------------------------------------------------------------
# deps
# ---------------------------------------------------------------------------


class TestAssetDeps:
    async def test_sends_deps_with_path(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(
            mock_bridge, "deps", asset_path="Assets/Prefabs/Player.prefab"
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "deps"
        assert params["assetPath"] == "Assets/Prefabs/Player.prefab"

    async def test_recursive_true_by_default(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(mock_bridge, "deps", asset_path="Assets/X.prefab")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        # recursive=True is default, so it should NOT be in params (only sent when False)
        assert "recursive" not in params

    async def test_recursive_false_included(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(
            mock_bridge, "deps", asset_path="Assets/X.prefab", recursive=False
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["recursive"] is False


# ---------------------------------------------------------------------------
# guid
# ---------------------------------------------------------------------------


class TestAssetGuid:
    async def test_sends_guid_with_path_input(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(
            mock_bridge, "guid", input_value="Assets/Prefabs/Player.prefab"
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "guid"
        assert params["input"] == "Assets/Prefabs/Player.prefab"

    async def test_sends_guid_with_hex_input(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(
            mock_bridge, "guid", input_value="abc123def456789012345678abcdef01"
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["input"] == "abc123def456789012345678abcdef01"


# ---------------------------------------------------------------------------
# hash
# ---------------------------------------------------------------------------


class TestAssetHash:
    async def test_sends_hash_with_asset_path(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(mock_bridge, "hash", asset_path="Assets/Scripts/Player.cs")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "hash"
        assert params["assetPath"] == "Assets/Scripts/Player.cs"

    async def test_hash_returns_command_result(self, mock_bridge: MagicMock) -> None:
        expected = CommandResult(
            success=True,
            data={
                "operation": "hash",
                "assetPath": "Assets/Scripts/Player.cs",
                "sha256": "abc123",
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await asset_extended_operation(
            mock_bridge, "hash", asset_path="Assets/Scripts/Player.cs"
        )
        assert result.data["sha256"] == "abc123"

    def test_csharp_hash_contract(self) -> None:
        root = Path(__file__).resolve().parents[2]
        handler_source = root.joinpath(
            "ClaudeCodeBridge", "AssetExtendedCommandHandler.cs"
        ).read_text(encoding="utf-8")
        helper_source = root.joinpath("ClaudeCodeBridge", "AssetExtendedHelpers.cs").read_text(
            encoding="utf-8"
        )
        model_source = root.joinpath("ClaudeCodeBridge", "AssetExtendedModels.cs").read_text(
            encoding="utf-8"
        )

        assert 'case "hash":' in handler_source
        assert "ExecuteHash" in helper_source
        assert "SHA256.Create" in helper_source
        assert "sha256" in model_source


# ---------------------------------------------------------------------------
# folder-create
# ---------------------------------------------------------------------------


class TestAssetFolderCreate:
    async def test_sends_folder_create(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(
            mock_bridge, "folder-create", folder_path="Assets/Data/Configs"
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "folder-create"
        assert params["folderPath"] == "Assets/Data/Configs"


# ---------------------------------------------------------------------------
# folder-list
# ---------------------------------------------------------------------------


class TestAssetFolderList:
    async def test_sends_folder_list(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(mock_bridge, "folder-list", folder_path="Assets/Prefabs")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "folder-list"
        assert params["folderPath"] == "Assets/Prefabs"


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------


class TestAssetExport:
    async def test_sends_export_with_paths_and_output(self, mock_bridge: MagicMock) -> None:
        paths = ["Assets/Prefabs/Player.prefab", "Assets/Materials/PlayerMat.mat"]
        await asset_extended_operation(
            mock_bridge,
            "export",
            asset_paths=paths,
            output_path="Exports/player.unitypackage",
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "export"
        assert params["assetPaths"] == paths
        assert params["outputPath"] == "Exports/player.unitypackage"

    async def test_include_dependencies_false(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(
            mock_bridge,
            "export",
            asset_paths=["Assets/X.prefab"],
            output_path="out.unitypackage",
            include_dependencies=False,
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["includeDependencies"] is False

    async def test_include_dependencies_true_omitted(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(
            mock_bridge,
            "export",
            asset_paths=["Assets/X.prefab"],
            output_path="out.unitypackage",
            include_dependencies=True,
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "includeDependencies" not in params


# ---------------------------------------------------------------------------
# import-package
# ---------------------------------------------------------------------------


class TestAssetImportPackage:
    async def test_sends_import_package(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(
            mock_bridge,
            "import-package",
            package_path="Downloads/ui-kit.unitypackage",
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "import-package"
        assert params["packagePath"] == "Downloads/ui-kit.unitypackage"

    async def test_interactive_flag_included(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(
            mock_bridge,
            "import-package",
            package_path="x.unitypackage",
            interactive=True,
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["interactive"] is True

    async def test_interactive_false_omitted(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(
            mock_bridge,
            "import-package",
            package_path="x.unitypackage",
            interactive=False,
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "interactive" not in params


# ---------------------------------------------------------------------------
# import-model
# ---------------------------------------------------------------------------


class TestAssetImportModel:
    async def test_sends_import_model_paths(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(
            mock_bridge,
            "import-model",
            source_path="C:/Models/character.fbx",
            destination_path="Assets/Models/character.fbx",
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "import-model"
        assert params["sourcePath"] == "C:/Models/character.fbx"
        assert params["destinationPath"] == "Assets/Models/character.fbx"
        assert "overwrite" not in params

    async def test_explicit_overwrite_is_sent_to_unity(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(
            mock_bridge,
            "import-model",
            source_path="C:/Models/character.fbx",
            destination_path="Assets/Models/character.fbx",
            overwrite=True,
        )

        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["overwrite"] is True

    def test_cli_exposes_explicit_overwrite_flag(self) -> None:
        result = CliRunner().invoke(app, ["asset-ext", "import-model", "--help"])

        assert result.exit_code == 0, result.output
        assert "--overwrite" in result.output

    def test_csharp_import_model_contract(self) -> None:
        root = Path(__file__).resolve().parents[2]
        handler_source = root.joinpath(
            "ClaudeCodeBridge", "AssetExtendedCommandHandler.cs"
        ).read_text(encoding="utf-8")
        helper_source = root.joinpath("ClaudeCodeBridge", "AssetExtendedHelpers.cs").read_text(
            encoding="utf-8"
        )
        model_source = root.joinpath("ClaudeCodeBridge", "AssetExtendedModels.cs").read_text(
            encoding="utf-8"
        )

        assert 'case "import-model":' in handler_source
        assert "ExecuteImportModel" in helper_source
        assert "AssetDatabase.GetImporterType" in helper_source
        assert "DefaultImporter" in helper_source
        assert "typeof(AssetImporter)" in helper_source
        assert '".gltf"' in helper_source
        assert '".glb"' in helper_source
        assert "importerType" in model_source


# ---------------------------------------------------------------------------
# Invalid operation
# ---------------------------------------------------------------------------


class TestInvalidOperation:
    async def test_raises_value_error(self, mock_bridge: MagicMock) -> None:
        with pytest.raises(ValueError, match="Invalid asset extended action"):
            await asset_extended_operation(mock_bridge, "not-a-real-op")

    async def test_timeout_passed_through(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(
            mock_bridge,
            "create",
            asset_path="Assets/X.asset",
            asset_type="Material",
            timeout=120.0,
        )
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 120.0

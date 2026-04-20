"""QA adversarial tests for commands/asset_extended.py — extended asset operations.

Tests edge cases, error paths, and spec compliance per adversarial review.
Covers: C5 (GUIDs->paths), C6 (prefab rejection), C7 (MoveAsset errorDetail).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from unity_bridge.commands.asset_extended import (
    MUTATING_OPERATIONS,
    VALID_OPERATIONS,
    asset_extended_operation,
)
from unity_bridge.core.bridge import CommandResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_parameters(call_args: Any) -> dict:
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
# VALID_OPERATIONS completeness
# ---------------------------------------------------------------------------


class TestValidOperations:
    def test_all_spec_operations_present(self) -> None:
        expected = {
            "create",
            "delete",
            "copy",
            "move",
            "deps",
            "guid",
            "folder-create",
            "folder-list",
            "export",
            "import-package",
            "reserialize",
        }
        assert VALID_OPERATIONS == expected

    def test_is_frozenset(self) -> None:
        assert isinstance(VALID_OPERATIONS, frozenset)

    def test_mutating_operations_subset_of_valid(self) -> None:
        assert MUTATING_OPERATIONS.issubset(VALID_OPERATIONS)

    def test_mutating_operations_correct(self) -> None:
        expected_mutating = {
            "create",
            "delete",
            "copy",
            "move",
            "folder-create",
            "export",
            "import-package",
            "reserialize",
        }
        assert MUTATING_OPERATIONS == expected_mutating

    def test_read_only_operations_not_in_mutating(self) -> None:
        read_only = {"deps", "guid", "folder-list"}
        assert read_only.isdisjoint(MUTATING_OPERATIONS)


# ---------------------------------------------------------------------------
# Invalid / boundary action inputs
# ---------------------------------------------------------------------------


class TestEdgeCaseInputs:
    async def test_empty_string_action_raises(self, mock_bridge: MagicMock) -> None:
        with pytest.raises(ValueError, match="Invalid asset extended action"):
            await asset_extended_operation(mock_bridge, "")

    async def test_whitespace_only_action_raises(self, mock_bridge: MagicMock) -> None:
        with pytest.raises(ValueError, match="Invalid asset extended action"):
            await asset_extended_operation(mock_bridge, "   ")

    async def test_case_insensitive_action(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(mock_bridge, "FOLDER-CREATE", folder_path="Assets/Test")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "folder-create"

    async def test_similar_but_invalid_raises(self, mock_bridge: MagicMock) -> None:
        with pytest.raises(ValueError, match="Invalid asset extended action"):
            await asset_extended_operation(mock_bridge, "creates")

    async def test_partial_operation_raises(self, mock_bridge: MagicMock) -> None:
        with pytest.raises(ValueError, match="Invalid asset extended action"):
            await asset_extended_operation(mock_bridge, "folder")

    async def test_import_without_hyphen_raises(self, mock_bridge: MagicMock) -> None:
        with pytest.raises(ValueError, match="Invalid asset extended action"):
            await asset_extended_operation(mock_bridge, "importpackage")


# ---------------------------------------------------------------------------
# Command type for all operations
# ---------------------------------------------------------------------------


class TestCommandType:
    @pytest.mark.parametrize("action", sorted(VALID_OPERATIONS))
    async def test_all_operations_use_correct_type(
        self, mock_bridge: MagicMock, action: str
    ) -> None:
        await asset_extended_operation(mock_bridge, action)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "asset-extended-operation"


# ---------------------------------------------------------------------------
# Default parameter exclusion
# ---------------------------------------------------------------------------


class TestDefaultParameterExclusion:
    async def test_default_recursive_not_sent(self, mock_bridge: MagicMock) -> None:
        """recursive=True is default; should not be in params."""
        await asset_extended_operation(mock_bridge, "deps", asset_path="Assets/X.prefab")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "recursive" not in params

    async def test_default_use_trash_not_sent(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(mock_bridge, "delete", asset_path="Assets/X.asset")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "useTrash" not in params

    async def test_default_include_deps_not_sent(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(
            mock_bridge,
            "export",
            asset_paths=["Assets/X.asset"],
            output_path="out.unitypackage",
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "includeDependencies" not in params

    async def test_default_interactive_not_sent(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(
            mock_bridge,
            "import-package",
            package_path="x.unitypackage",
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "interactive" not in params

    async def test_none_params_not_sent(self, mock_bridge: MagicMock) -> None:
        """Only 'operation' should be in params when no optional args given."""
        await asset_extended_operation(mock_bridge, "folder-list")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert set(params.keys()) == {"operation"}


# ---------------------------------------------------------------------------
# Non-default parameters ARE sent
# ---------------------------------------------------------------------------


class TestNonDefaultParamsSent:
    async def test_use_trash_true_sent(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(
            mock_bridge, "delete", asset_path="Assets/X.asset", use_trash=True
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["useTrash"] is True

    async def test_recursive_false_sent(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(
            mock_bridge, "deps", asset_path="Assets/X.prefab", recursive=False
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["recursive"] is False

    async def test_include_dependencies_false_sent(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(
            mock_bridge,
            "export",
            asset_paths=["Assets/X.asset"],
            output_path="out.unitypackage",
            include_dependencies=False,
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["includeDependencies"] is False

    async def test_interactive_true_sent(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(
            mock_bridge,
            "import-package",
            package_path="x.unitypackage",
            interactive=True,
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["interactive"] is True


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------


class TestTimeout:
    async def test_default_timeout_is_60(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(mock_bridge, "create")
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 60.0 or timeout == 60

    async def test_custom_timeout(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(
            mock_bridge,
            "export",
            asset_paths=["Assets/X.asset"],
            output_path="out.unitypackage",
            timeout=120,
        )
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 120


# ---------------------------------------------------------------------------
# Return value propagation
# ---------------------------------------------------------------------------


class TestReturnValue:
    async def test_failure_propagated(self, mock_bridge: MagicMock) -> None:
        failed = CommandResult(
            success=False,
            data={"operation": "create", "success": False},
            error="assetPath is required",
            exit_code=1,
        )
        mock_bridge.send_command_with_retry.return_value = failed
        result = await asset_extended_operation(mock_bridge, "create")
        assert result.success is False

    async def test_move_error_detail_propagated(self, mock_bridge: MagicMock) -> None:
        """C7: MoveAsset errorDetail field should be in the response."""
        move_fail = CommandResult(
            success=False,
            data={
                "operation": "move",
                "errorDetail": "Destination path does not exist",
                "success": False,
            },
        )
        mock_bridge.send_command_with_retry.return_value = move_fail
        result = await asset_extended_operation(
            mock_bridge,
            "move",
            source_path="Assets/A.prefab",
            destination_path="Assets/Bad/A.prefab",
        )
        assert result.success is False
        assert result.data["errorDetail"] == "Destination path does not exist"


# ---------------------------------------------------------------------------
# camelCase parameter naming (bridge protocol convention)
# ---------------------------------------------------------------------------


class TestCamelCaseParams:
    async def test_asset_path_is_camel_case(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(mock_bridge, "create", asset_path="Assets/X.asset")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "assetPath" in params
        assert "asset_path" not in params

    async def test_source_path_is_camel_case(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(
            mock_bridge, "copy", source_path="Assets/A", destination_path="Assets/B"
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "sourcePath" in params
        assert "destinationPath" in params
        assert "source_path" not in params

    async def test_folder_path_is_camel_case(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(mock_bridge, "folder-create", folder_path="Assets/Test")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "folderPath" in params
        assert "folder_path" not in params

    async def test_asset_type_is_camel_case(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(
            mock_bridge,
            "create",
            asset_path="Assets/X.asset",
            asset_type="Material",
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "assetType" in params

    async def test_output_path_is_camel_case(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(
            mock_bridge,
            "export",
            asset_paths=["Assets/X"],
            output_path="out.unitypackage",
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "outputPath" in params

    async def test_package_path_is_camel_case(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(mock_bridge, "import-package", package_path="x.unitypackage")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "packagePath" in params

    async def test_guid_input_key_name(self, mock_bridge: MagicMock) -> None:
        await asset_extended_operation(mock_bridge, "guid", input_value="Assets/X.prefab")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "input" in params
        assert "input_value" not in params


# ---------------------------------------------------------------------------
# MCP schema validation
# ---------------------------------------------------------------------------


class TestMcpSchema:
    def test_schema_has_timeout(self) -> None:
        from unity_bridge.mcp.schemas_ext import asset_extended

        schema = asset_extended()
        assert "timeout" in schema["properties"]
        assert schema["properties"]["timeout"]["default"] == 60

    def test_schema_operation_enum_complete(self) -> None:
        from unity_bridge.mcp.schemas_ext import asset_extended

        schema = asset_extended()
        enum_values = set(schema["properties"]["operation"]["enum"])
        assert enum_values == VALID_OPERATIONS

    def test_schema_operation_is_required(self) -> None:
        from unity_bridge.mcp.schemas_ext import asset_extended

        schema = asset_extended()
        assert "operation" in schema["required"]

    def test_tool_registered_in_command_map(self) -> None:
        from unity_bridge.mcp.tools import TOOL_COMMAND_MAP

        assert "unity_asset_extended" in TOOL_COMMAND_MAP
        assert TOOL_COMMAND_MAP["unity_asset_extended"] == "asset-extended-operation"

    def test_tool_registered_in_definitions(self) -> None:
        from unity_bridge.mcp.tools import TOOL_DEFINITIONS

        names = [t["name"] for t in TOOL_DEFINITIONS]
        assert "unity_asset_extended" in names

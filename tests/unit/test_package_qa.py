"""QA adversarial tests for commands/package.py — Package Manager operations.

Tests edge cases, spec compliance per adversarial review findings.
Covers: M1 (Resolve void), parameter exclusion, camelCase naming, MCP schema.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from unity_bridge.commands.package import (
    VALID_OPERATIONS,
    package_operation,
)
from unity_bridge.core.bridge import CommandResult

ROOT = Path(__file__).resolve().parents[2]


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
            "list",
            "search",
            "search-all",
            "add",
            "remove",
            "info",
            "embed",
            "resolve",
        }
        assert VALID_OPERATIONS == expected

    def test_is_frozenset(self) -> None:
        assert isinstance(VALID_OPERATIONS, frozenset)


# ---------------------------------------------------------------------------
# Edge case inputs
# ---------------------------------------------------------------------------


class TestEdgeCaseInputs:
    async def test_empty_string_action_raises(self, mock_bridge: MagicMock) -> None:
        with pytest.raises(ValueError, match="Invalid package action"):
            await package_operation(mock_bridge, "")

    async def test_whitespace_only_action_raises(self, mock_bridge: MagicMock) -> None:
        with pytest.raises(ValueError, match="Invalid package action"):
            await package_operation(mock_bridge, "   ")

    async def test_case_insensitive_action(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "SEARCH-ALL")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "search-all"

    async def test_mixed_case_action(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "Search-All")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "search-all"

    async def test_similar_but_invalid_raises(self, mock_bridge: MagicMock) -> None:
        with pytest.raises(ValueError, match="Invalid package action"):
            await package_operation(mock_bridge, "install")

    async def test_searchall_no_hyphen_raises(self, mock_bridge: MagicMock) -> None:
        with pytest.raises(ValueError, match="Invalid package action"):
            await package_operation(mock_bridge, "searchall")

    async def test_import_package_raises(self, mock_bridge: MagicMock) -> None:
        """import-package is asset_extended, not package manager."""
        with pytest.raises(ValueError, match="Invalid package action"):
            await package_operation(mock_bridge, "import-package")

    async def test_leading_trailing_whitespace_stripped(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "  add  ", identifier="com.unity.foo@1.0.0")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "add"


# ---------------------------------------------------------------------------
# Command type for all operations
# ---------------------------------------------------------------------------


class TestCommandType:
    @pytest.mark.parametrize("action", sorted(VALID_OPERATIONS))
    async def test_all_operations_use_correct_type(
        self, mock_bridge: MagicMock, action: str
    ) -> None:
        await package_operation(mock_bridge, action)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "package-operation"


# ---------------------------------------------------------------------------
# Parameter exclusion: defaults not sent
# ---------------------------------------------------------------------------


class TestParameterExclusion:
    async def test_offline_mode_false_not_sent(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "list", offline_mode=False)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "offlineMode" not in params

    async def test_include_indirect_false_not_sent(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "list", include_indirect=False)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "includeIndirectDependencies" not in params

    async def test_none_identifier_not_sent(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "add")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "identifier" not in params

    async def test_none_package_name_not_sent(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "remove")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "packageName" not in params

    async def test_none_query_not_sent(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "search")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "query" not in params

    async def test_none_source_not_sent(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "list")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "source" not in params

    async def test_resolve_only_operation_param(self, mock_bridge: MagicMock) -> None:
        """Resolve sends nothing extra — M1: Client.Resolve() is void."""
        await package_operation(mock_bridge, "resolve")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert set(params.keys()) == {"operation"}

    async def test_list_minimal_only_operation(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "list")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert set(params.keys()) == {"operation"}


# ---------------------------------------------------------------------------
# Non-default parameters ARE sent
# ---------------------------------------------------------------------------


class TestNonDefaultParamsSent:
    async def test_offline_mode_true_sent(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "list", offline_mode=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["offlineMode"] is True

    async def test_include_indirect_true_sent(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "list", include_indirect=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["includeIndirectDependencies"] is True

    async def test_source_filter_sent(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "list", source="git")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["source"] == "git"

    async def test_identifier_sent(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "add", identifier="com.unity.foo@1.0.0")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["identifier"] == "com.unity.foo@1.0.0"

    async def test_package_name_sent(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "info", package_name="com.unity.foo")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["packageName"] == "com.unity.foo"

    async def test_query_sent(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "search", query="textmeshpro")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["query"] == "textmeshpro"


# ---------------------------------------------------------------------------
# camelCase parameter naming
# ---------------------------------------------------------------------------


class TestCamelCaseParams:
    async def test_package_name_is_camel_case(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "remove", package_name="com.unity.foo")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "packageName" in params
        assert "package_name" not in params

    async def test_offline_mode_is_camel_case(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "list", offline_mode=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "offlineMode" in params
        assert "offline_mode" not in params

    async def test_include_indirect_is_camel_case(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "list", include_indirect=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "includeIndirectDependencies" in params
        assert "include_indirect" not in params


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------


class TestTimeout:
    async def test_default_timeout_is_60(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "list")
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 60.0 or timeout == 60

    async def test_custom_timeout(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "add", identifier="x", timeout=120)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 120

    async def test_zero_timeout(self, mock_bridge: MagicMock) -> None:
        await package_operation(mock_bridge, "list", timeout=0)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 0


# ---------------------------------------------------------------------------
# Return value propagation
# ---------------------------------------------------------------------------


class TestReturnValue:
    async def test_success_propagated(self, mock_bridge: MagicMock) -> None:
        response = CommandResult(
            success=True,
            data={
                "operation": "list",
                "packages": [{"name": "com.unity.foo", "version": "1.0.0"}],
                "totalCount": 1,
            },
        )
        mock_bridge.send_command_with_retry.return_value = response
        result = await package_operation(mock_bridge, "list")
        assert result.success is True
        assert result.data["totalCount"] == 1

    async def test_failure_propagated(self, mock_bridge: MagicMock) -> None:
        failed = CommandResult(
            success=False,
            data={"operation": "add", "success": False},
            error="Package not found: com.unity.nonexistent",
            exit_code=1,
        )
        mock_bridge.send_command_with_retry.return_value = failed
        result = await package_operation(mock_bridge, "add", identifier="com.unity.nonexistent")
        assert result.success is False
        assert "not found" in result.error

    async def test_resolve_void_success(self, mock_bridge: MagicMock) -> None:
        """M1: Client.Resolve() returns void — success is immediate."""
        response = CommandResult(
            success=True,
            data={
                "operation": "resolve",
                "success": True,
                "message": "Package resolution triggered.",
            },
        )
        mock_bridge.send_command_with_retry.return_value = response
        result = await package_operation(mock_bridge, "resolve")
        assert result.success is True

    async def test_embed_conflict_error(self, mock_bridge: MagicMock) -> None:
        """Embed can fail if the package is already embedded."""
        response = CommandResult(
            success=False,
            data={
                "operation": "embed",
                "success": False,
                "message": "Package is already embedded.",
            },
        )
        mock_bridge.send_command_with_retry.return_value = response
        result = await package_operation(mock_bridge, "embed", package_name="com.unity.foo")
        assert result.success is False
        assert "already embedded" in result.data["message"]


# ---------------------------------------------------------------------------
# All parameters combined for list
# ---------------------------------------------------------------------------


class TestListAllParams:
    async def test_all_list_params_together(self, mock_bridge: MagicMock) -> None:
        await package_operation(
            mock_bridge,
            "list",
            source="registry",
            offline_mode=True,
            include_indirect=True,
            timeout=90,
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "list"
        assert params["source"] == "registry"
        assert params["offlineMode"] is True
        assert params["includeIndirectDependencies"] is True
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 90


# ---------------------------------------------------------------------------
# MCP schema validation
# ---------------------------------------------------------------------------


class TestMcpSchema:
    def test_schema_has_timeout(self) -> None:
        from unity_bridge.mcp.schemas_ext import package_operation as pkg_schema

        schema = pkg_schema()
        assert "timeout" in schema["properties"]
        assert schema["properties"]["timeout"]["default"] == 60

    def test_schema_operation_enum_complete(self) -> None:
        from unity_bridge.mcp.schemas_ext import package_operation as pkg_schema

        schema = pkg_schema()
        enum_values = set(schema["properties"]["operation"]["enum"])
        assert enum_values == VALID_OPERATIONS

    def test_schema_operation_is_required(self) -> None:
        from unity_bridge.mcp.schemas_ext import package_operation as pkg_schema

        schema = pkg_schema()
        assert "operation" in schema["required"]

    def test_schema_source_enum(self) -> None:
        from unity_bridge.mcp.schemas_ext import package_operation as pkg_schema

        schema = pkg_schema()
        source_enum = set(schema["properties"]["source"]["enum"])
        assert source_enum == {"registry", "git", "embedded", "local"}

    def test_tool_registered_in_command_map(self) -> None:
        from unity_bridge.mcp.tools import TOOL_COMMAND_MAP

        assert "unity_package_operation" in TOOL_COMMAND_MAP
        assert TOOL_COMMAND_MAP["unity_package_operation"] == "package-operation"

    def test_tool_registered_in_definitions(self) -> None:
        from unity_bridge.mcp.tools import TOOL_DEFINITIONS

        names = [t["name"] for t in TOOL_DEFINITIONS]
        assert "unity_package_operation" in names


class TestCSharpPackageHandler:
    def test_source_filter_is_applied_after_package_list_completes(self) -> None:
        source = (ROOT / "ClaudeCodeBridge" / "PackageManagerCommandHandler.cs").read_text()

        assert 'RegisterPending(command, request, "list", source)' in source
        assert "MatchesSourceFilter(pkg, pending.Context)" in source
        assert "NormalizeSourceFilter(parameters.source)" in source

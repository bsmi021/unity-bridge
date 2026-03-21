"""Unit tests for commands/testing.py — test listing operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from unity_bridge.core.bridge import CommandResult


def _import_testing():
    from unity_bridge.commands import testing

    return testing


# ---------------------------------------------------------------------------
# list tests (default mode)
# ---------------------------------------------------------------------------


class TestListTests:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_testing()
        await mod.list_tests(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "list-tests"

    async def test_default_mode_is_tests(self, mock_bridge: MagicMock) -> None:
        mod = _import_testing()
        await mod.list_tests(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["mode"] == "tests"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_testing()
        await mod.list_tests(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        timeout = _extract_kwarg(call_args, "timeout")
        assert timeout == 30.0 or timeout == 30

    async def test_custom_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_testing()
        await mod.list_tests(mock_bridge, timeout=60)
        call_args = mock_bridge.send_command_with_retry.call_args
        timeout = _extract_kwarg(call_args, "timeout")
        assert timeout == 60.0 or timeout == 60

    async def test_optional_params_excluded_by_default(self, mock_bridge: MagicMock) -> None:
        mod = _import_testing()
        await mod.list_tests(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert "testPlatform" not in params
        assert "filter" not in params

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_testing()
        expected = CommandResult(
            success=True,
            data={
                "tests": [
                    {
                        "fullName": "Tests.Combat.CombatTests.AttackDealsDamage",
                        "className": "CombatTests",
                        "methodName": "AttackDealsDamage",
                    }
                ],
                "count": 1,
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.list_tests(mock_bridge)
        assert result.success is True
        assert result.data["count"] == 1


# ---------------------------------------------------------------------------
# list tests with platform filter
# ---------------------------------------------------------------------------


class TestListTestsPlatform:
    async def test_includes_platform(self, mock_bridge: MagicMock) -> None:
        mod = _import_testing()
        await mod.list_tests(mock_bridge, platform="EditMode")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["testPlatform"] == "EditMode"

    async def test_playmode_platform(self, mock_bridge: MagicMock) -> None:
        mod = _import_testing()
        await mod.list_tests(mock_bridge, platform="PlayMode")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["testPlatform"] == "PlayMode"


# ---------------------------------------------------------------------------
# list tests with filter
# ---------------------------------------------------------------------------


class TestListTestsFilter:
    async def test_includes_filter(self, mock_bridge: MagicMock) -> None:
        mod = _import_testing()
        await mod.list_tests(mock_bridge, filter_pattern="Combat*")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["filter"] == "Combat*"


# ---------------------------------------------------------------------------
# list categories mode
# ---------------------------------------------------------------------------


class TestListCategories:
    async def test_sends_categories_mode(self, mock_bridge: MagicMock) -> None:
        mod = _import_testing()
        await mod.list_tests(mock_bridge, mode="categories")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["mode"] == "categories"

    async def test_returns_categories(self, mock_bridge: MagicMock) -> None:
        mod = _import_testing()
        expected = CommandResult(
            success=True,
            data={"categories": ["Combat", "Unit", "Integration"]},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.list_tests(mock_bridge, mode="categories")
        assert result.success is True
        assert "Combat" in result.data["categories"]


# ---------------------------------------------------------------------------
# list assemblies mode
# ---------------------------------------------------------------------------


class TestListAssemblies:
    async def test_sends_assemblies_mode(self, mock_bridge: MagicMock) -> None:
        mod = _import_testing()
        await mod.list_tests(mock_bridge, mode="assemblies")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["mode"] == "assemblies"

    async def test_returns_assemblies(self, mock_bridge: MagicMock) -> None:
        mod = _import_testing()
        expected = CommandResult(
            success=True,
            data={"assemblies": [{"name": "Assembly-CSharp-Editor-Tests", "testCount": 47}]},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.list_tests(mock_bridge, mode="assemblies")
        assert result.success is True
        assert result.data["assemblies"][0]["testCount"] == 47


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    async def test_invalid_mode_raises(self, mock_bridge: MagicMock) -> None:
        mod = _import_testing()
        with pytest.raises(ValueError, match="Invalid list mode"):
            await mod.list_tests(mock_bridge, mode="invalid")

    async def test_mode_normalised(self, mock_bridge: MagicMock) -> None:
        mod = _import_testing()
        await mod.list_tests(mock_bridge, mode="  TESTS  ")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["mode"] == "tests"


# ---------------------------------------------------------------------------
# Combined parameters
# ---------------------------------------------------------------------------


class TestCombinedParams:
    async def test_all_params_together(self, mock_bridge: MagicMock) -> None:
        mod = _import_testing()
        await mod.list_tests(
            mock_bridge,
            mode="tests",
            platform="PlayMode",
            filter_pattern="Movement*",
            timeout=45,
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["mode"] == "tests"
        assert params["testPlatform"] == "PlayMode"
        assert params["filter"] == "Movement*"
        timeout = _extract_kwarg(call_args, "timeout")
        assert timeout == 45.0 or timeout == 45


# ---------------------------------------------------------------------------
# MCP schema
# ---------------------------------------------------------------------------


class TestSchema:
    def test_list_tests_schema_structure(self) -> None:
        from unity_bridge.mcp.schemas_ext import list_tests

        schema = list_tests()
        assert schema["type"] == "object"
        assert "mode" in schema["properties"]

    def test_list_tests_schema_modes(self) -> None:
        from unity_bridge.mcp.schemas_ext import list_tests

        schema = list_tests()
        modes = schema["properties"]["mode"]["enum"]
        assert set(modes) == {"tests", "categories", "assemblies"}

    def test_list_tests_schema_platforms(self) -> None:
        from unity_bridge.mcp.schemas_ext import list_tests

        schema = list_tests()
        platforms = schema["properties"]["testPlatform"]["enum"]
        assert set(platforms) == {"EditMode", "PlayMode"}

    def test_list_tests_schema_has_timeout(self) -> None:
        from unity_bridge.mcp.schemas_ext import list_tests

        schema = list_tests()
        assert "timeout" in schema["properties"]


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


class TestToolRegistration:
    def test_tool_in_command_map(self) -> None:
        from unity_bridge.mcp.tools import TOOL_COMMAND_MAP

        assert "unity_list_tests" in TOOL_COMMAND_MAP
        assert TOOL_COMMAND_MAP["unity_list_tests"] == "list-tests"

    def test_tool_in_definitions(self) -> None:
        from unity_bridge.mcp.tools import TOOL_DEFINITIONS

        names = [t["name"] for t in TOOL_DEFINITIONS]
        assert "unity_list_tests" in names


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class TestProtocol:
    def test_timeout_default_in_protocol(self) -> None:
        from unity_bridge.core.protocol import TIMEOUT_DEFAULTS

        assert "list-tests" in TIMEOUT_DEFAULTS
        assert TIMEOUT_DEFAULTS["list-tests"] == 30

    def test_parallel_safe(self) -> None:
        from unity_bridge.core.protocol import PARALLEL_SAFE_COMMANDS

        assert "list-tests" in PARALLEL_SAFE_COMMANDS


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

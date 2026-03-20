"""Unit tests for commands/compile_extended.py — compilation pipeline operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from unity_bridge.core.bridge import CommandResult


def _import_compile_ext():
    from unity_bridge.commands import compile_extended

    return compile_extended


# ---------------------------------------------------------------------------
# assemblies operation
# ---------------------------------------------------------------------------


class TestAssemblies:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_compile_ext()
        await mod.compile_assemblies(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "compilation-pipeline"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_compile_ext()
        await mod.compile_assemblies(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "assemblies"
        assert len(params) == 1

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_compile_ext()
        await mod.compile_assemblies(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        timeout = _extract_kwarg(call_args, "timeout")
        assert timeout == 15.0 or timeout == 15

    async def test_custom_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_compile_ext()
        await mod.compile_assemblies(mock_bridge, timeout=60)
        call_args = mock_bridge.send_command_with_retry.call_args
        timeout = _extract_kwarg(call_args, "timeout")
        assert timeout == 60.0 or timeout == 60

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_compile_ext()
        expected = CommandResult(
            success=True,
            data={"assemblies": [{"name": "Assembly-CSharp"}]},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.compile_assemblies(mock_bridge)
        assert result.success is True
        assert result.data["assemblies"][0]["name"] == "Assembly-CSharp"


# ---------------------------------------------------------------------------
# defines operation
# ---------------------------------------------------------------------------


class TestDefines:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_compile_ext()
        await mod.compile_defines(mock_bridge, assembly_name="Assembly-CSharp")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "compilation-pipeline"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_compile_ext()
        await mod.compile_defines(mock_bridge, assembly_name="Assembly-CSharp")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "defines"
        assert params["assemblyName"] == "Assembly-CSharp"

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_compile_ext()
        expected = CommandResult(
            success=True,
            data={"defines": ["UNITY_EDITOR", "UNITY_6000_0_OR_NEWER"]},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.compile_defines(mock_bridge, assembly_name="Assembly-CSharp")
        assert result.success is True
        assert "UNITY_EDITOR" in result.data["defines"]


# ---------------------------------------------------------------------------
# which operation
# ---------------------------------------------------------------------------


class TestWhich:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_compile_ext()
        await mod.compile_which(mock_bridge, script_path="Assets/Scripts/Player.cs")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "compilation-pipeline"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_compile_ext()
        await mod.compile_which(mock_bridge, script_path="Assets/Scripts/Player.cs")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "which"
        assert params["scriptPath"] == "Assets/Scripts/Player.cs"

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_compile_ext()
        expected = CommandResult(
            success=True,
            data={
                "scriptPath": "Assets/Scripts/Player.cs",
                "assembly": "Assembly-CSharp",
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.compile_which(mock_bridge, script_path="Assets/Scripts/Player.cs")
        assert result.success is True
        assert result.data["assembly"] == "Assembly-CSharp"


# ---------------------------------------------------------------------------
# optimization operation (get)
# ---------------------------------------------------------------------------


class TestOptimizationGet:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_compile_ext()
        await mod.compile_optimization(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "compilation-pipeline"

    async def test_sends_correct_parameters_no_mode(self, mock_bridge: MagicMock) -> None:
        mod = _import_compile_ext()
        await mod.compile_optimization(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "optimization"
        assert "mode" not in params

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_compile_ext()
        expected = CommandResult(
            success=True,
            data={"mode": "Debug", "changed": False},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.compile_optimization(mock_bridge)
        assert result.success is True
        assert result.data["mode"] == "Debug"
        assert result.data["changed"] is False


# ---------------------------------------------------------------------------
# optimization operation (set)
# ---------------------------------------------------------------------------


class TestOptimizationSet:
    async def test_sends_mode_parameter(self, mock_bridge: MagicMock) -> None:
        mod = _import_compile_ext()
        await mod.compile_optimization(mock_bridge, mode="Release")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "optimization"
        assert params["mode"] == "Release"

    async def test_none_mode(self, mock_bridge: MagicMock) -> None:
        mod = _import_compile_ext()
        await mod.compile_optimization(mock_bridge, mode="None")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["mode"] == "None"

    async def test_debug_mode(self, mock_bridge: MagicMock) -> None:
        mod = _import_compile_ext()
        await mod.compile_optimization(mock_bridge, mode="Debug")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["mode"] == "Debug"


# ---------------------------------------------------------------------------
# Generic operation function
# ---------------------------------------------------------------------------


class TestGenericOperation:
    async def test_assemblies_via_generic(self, mock_bridge: MagicMock) -> None:
        mod = _import_compile_ext()
        await mod.compilation_pipeline_operation(mock_bridge, operation="assemblies")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "assemblies"

    async def test_defines_via_generic(self, mock_bridge: MagicMock) -> None:
        mod = _import_compile_ext()
        await mod.compilation_pipeline_operation(
            mock_bridge, operation="defines", assembly_name="MyAssembly"
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "defines"
        assert params["assemblyName"] == "MyAssembly"

    async def test_which_via_generic(self, mock_bridge: MagicMock) -> None:
        mod = _import_compile_ext()
        await mod.compilation_pipeline_operation(
            mock_bridge, operation="which", script_path="Assets/Scripts/Foo.cs"
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "which"
        assert params["scriptPath"] == "Assets/Scripts/Foo.cs"

    async def test_optimization_via_generic(self, mock_bridge: MagicMock) -> None:
        mod = _import_compile_ext()
        await mod.compilation_pipeline_operation(
            mock_bridge, operation="optimization", mode="Release"
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "optimization"
        assert params["mode"] == "Release"

    async def test_optional_params_excluded(self, mock_bridge: MagicMock) -> None:
        mod = _import_compile_ext()
        await mod.compilation_pipeline_operation(mock_bridge, operation="assemblies")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert "assemblyName" not in params
        assert "scriptPath" not in params
        assert "mode" not in params


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    async def test_invalid_operation_raises(self, mock_bridge: MagicMock) -> None:
        mod = _import_compile_ext()
        with pytest.raises(ValueError, match="Invalid compilation pipeline operation"):
            await mod.compilation_pipeline_operation(mock_bridge, operation="invalid")

    async def test_operation_normalised(self, mock_bridge: MagicMock) -> None:
        mod = _import_compile_ext()
        await mod.compilation_pipeline_operation(mock_bridge, operation="  ASSEMBLIES  ")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "assemblies"


# ---------------------------------------------------------------------------
# MCP schema
# ---------------------------------------------------------------------------


class TestSchema:
    def test_compilation_pipeline_schema_structure(self) -> None:
        from unity_bridge.mcp.schemas_ext import compilation_pipeline

        schema = compilation_pipeline()
        assert schema["type"] == "object"
        assert "operation" in schema["properties"]
        assert schema["required"] == ["operation"]

    def test_compilation_pipeline_schema_operations(self) -> None:
        from unity_bridge.mcp.schemas_ext import compilation_pipeline

        schema = compilation_pipeline()
        ops = schema["properties"]["operation"]["enum"]
        assert set(ops) == {"assemblies", "defines", "which", "optimization"}

    def test_compilation_pipeline_schema_mode_values(self) -> None:
        from unity_bridge.mcp.schemas_ext import compilation_pipeline

        schema = compilation_pipeline()
        modes = schema["properties"]["mode"]["enum"]
        assert set(modes) == {"None", "Debug", "Release"}

    def test_compilation_pipeline_schema_has_timeout(self) -> None:
        from unity_bridge.mcp.schemas_ext import compilation_pipeline

        schema = compilation_pipeline()
        assert "timeout" in schema["properties"]


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


class TestToolRegistration:
    def test_tool_in_command_map(self) -> None:
        from unity_bridge.mcp.tools import TOOL_COMMAND_MAP

        assert "unity_compilation_pipeline" in TOOL_COMMAND_MAP
        assert TOOL_COMMAND_MAP["unity_compilation_pipeline"] == "compilation-pipeline"

    def test_tool_in_definitions(self) -> None:
        from unity_bridge.mcp.tools import TOOL_DEFINITIONS

        names = [t["name"] for t in TOOL_DEFINITIONS]
        assert "unity_compilation_pipeline" in names


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class TestProtocol:
    def test_timeout_default_in_protocol(self) -> None:
        from unity_bridge.core.protocol import TIMEOUT_DEFAULTS

        assert "compilation-pipeline" in TIMEOUT_DEFAULTS
        assert TIMEOUT_DEFAULTS["compilation-pipeline"] == 15

    def test_not_parallel_safe(self) -> None:
        from unity_bridge.core.protocol import PARALLEL_SAFE_COMMANDS

        assert "compilation-pipeline" not in PARALLEL_SAFE_COMMANDS


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

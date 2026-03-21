"""Unit tests for commands/shader.py — all 6 shader inspection operations.

Tests cover:
- All 6 operations send correct command type and parameters
- Input validation (invalid operation, missing required params)
- Parameter forwarding (camelCase keys, optional fields)
- Edge cases: empty shader name, whitespace, errors-only filter
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from unity_bridge.commands.shader import (
    VALID_OPERATIONS,
    shader_errors,
    shader_find_by_property,
    shader_info,
    shader_inspection_operation,
    shader_keywords,
    shader_list,
    shader_properties,
)


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
# shader list
# ---------------------------------------------------------------------------


class TestShaderList:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await shader_list(mock_bridge)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "shader-inspection"

    async def test_default_params(self, mock_bridge: MagicMock) -> None:
        await shader_list(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "list"
        assert params["errorsOnly"] is False

    async def test_errors_only_filter(self, mock_bridge: MagicMock) -> None:
        await shader_list(mock_bridge, errors_only=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["errorsOnly"] is True

    async def test_custom_timeout(self, mock_bridge: MagicMock) -> None:
        await shader_list(mock_bridge, timeout=60.0)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 60.0


# ---------------------------------------------------------------------------
# shader info
# ---------------------------------------------------------------------------


class TestShaderInfo:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await shader_info(mock_bridge, "Universal Render Pipeline/Lit")
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "shader-inspection"

    async def test_includes_shader_name(self, mock_bridge: MagicMock) -> None:
        await shader_info(mock_bridge, "Universal Render Pipeline/Lit")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "info"
        assert params["shaderName"] == "Universal Render Pipeline/Lit"

    async def test_shader_name_with_slashes(self, mock_bridge: MagicMock) -> None:
        """Shader names contain forward slashes — verify they pass through."""
        name = "Custom/Category/SubCategory/MyShader"
        await shader_info(mock_bridge, name)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["shaderName"] == name

    async def test_shader_name_with_spaces(self, mock_bridge: MagicMock) -> None:
        """Shader names can contain spaces."""
        name = "My Custom Shader"
        await shader_info(mock_bridge, name)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["shaderName"] == name


# ---------------------------------------------------------------------------
# shader errors
# ---------------------------------------------------------------------------


class TestShaderErrors:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await shader_errors(mock_bridge, "Custom/BrokenShader")
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "shader-inspection"

    async def test_includes_shader_name(self, mock_bridge: MagicMock) -> None:
        await shader_errors(mock_bridge, "Custom/BrokenShader")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "errors"
        assert params["shaderName"] == "Custom/BrokenShader"


# ---------------------------------------------------------------------------
# shader properties
# ---------------------------------------------------------------------------


class TestShaderProperties:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await shader_properties(mock_bridge, "Universal Render Pipeline/Lit")
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "shader-inspection"

    async def test_includes_shader_name(self, mock_bridge: MagicMock) -> None:
        await shader_properties(mock_bridge, "Standard")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "properties"
        assert params["shaderName"] == "Standard"


# ---------------------------------------------------------------------------
# shader find-by-property
# ---------------------------------------------------------------------------


class TestShaderFindByProperty:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await shader_find_by_property(mock_bridge, "_MainTex")
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "shader-inspection"

    async def test_includes_property_name(self, mock_bridge: MagicMock) -> None:
        await shader_find_by_property(mock_bridge, "_MainTex")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "find-by-property"
        assert params["propertyName"] == "_MainTex"

    async def test_property_name_with_underscore_prefix(self, mock_bridge: MagicMock) -> None:
        """Shader properties typically start with underscore."""
        await shader_find_by_property(mock_bridge, "_BumpMap")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["propertyName"] == "_BumpMap"


# ---------------------------------------------------------------------------
# shader keywords
# ---------------------------------------------------------------------------


class TestShaderKeywords:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await shader_keywords(mock_bridge, "Universal Render Pipeline/Lit")
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "shader-inspection"

    async def test_default_no_filter(self, mock_bridge: MagicMock) -> None:
        await shader_keywords(mock_bridge, "Universal Render Pipeline/Lit")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "keywords"
        assert params["shaderName"] == "Universal Render Pipeline/Lit"
        assert "keywordFilter" not in params

    async def test_global_filter(self, mock_bridge: MagicMock) -> None:
        await shader_keywords(mock_bridge, "Standard", keyword_filter="global")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["keywordFilter"] == "global"

    async def test_local_filter(self, mock_bridge: MagicMock) -> None:
        await shader_keywords(mock_bridge, "Standard", keyword_filter="local")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["keywordFilter"] == "local"

    async def test_none_filter_omits_key(self, mock_bridge: MagicMock) -> None:
        """When keyword_filter is None, keywordFilter should not be in params."""
        await shader_keywords(mock_bridge, "Standard", keyword_filter=None)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "keywordFilter" not in params


# ---------------------------------------------------------------------------
# Generic shader_inspection_operation (MCP dispatch)
# ---------------------------------------------------------------------------


class TestShaderInspectionOperation:
    async def test_valid_operations_set_complete(self) -> None:
        """Ensure VALID_OPERATIONS contains all 6 expected operations."""
        expected = {"list", "info", "errors", "properties", "find-by-property", "keywords"}
        assert VALID_OPERATIONS == expected

    async def test_invalid_operation_raises(self, mock_bridge: MagicMock) -> None:
        with pytest.raises(ValueError, match="Invalid shader inspection operation"):
            await shader_inspection_operation(mock_bridge, "nonexistent")

    async def test_empty_operation_raises(self, mock_bridge: MagicMock) -> None:
        with pytest.raises(ValueError, match="Invalid shader inspection operation"):
            await shader_inspection_operation(mock_bridge, "")

    async def test_operation_normalized_to_lowercase(self, mock_bridge: MagicMock) -> None:
        await shader_inspection_operation(mock_bridge, "LIST")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "list"

    async def test_operation_stripped(self, mock_bridge: MagicMock) -> None:
        await shader_inspection_operation(mock_bridge, "  info  ")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "info"

    async def test_list_with_errors_only(self, mock_bridge: MagicMock) -> None:
        await shader_inspection_operation(mock_bridge, "list", errors_only=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["errorsOnly"] is True

    async def test_list_without_errors_only_omits_key(self, mock_bridge: MagicMock) -> None:
        """When errors_only is False (default), errorsOnly should not be in params."""
        await shader_inspection_operation(mock_bridge, "list")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "errorsOnly" not in params

    async def test_info_passes_shader_name(self, mock_bridge: MagicMock) -> None:
        await shader_inspection_operation(
            mock_bridge, "info", shader_name="Universal Render Pipeline/Lit"
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["shaderName"] == "Universal Render Pipeline/Lit"

    async def test_find_by_property_passes_property_name(self, mock_bridge: MagicMock) -> None:
        await shader_inspection_operation(mock_bridge, "find-by-property", property_name="_MainTex")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["propertyName"] == "_MainTex"

    async def test_keywords_passes_filter(self, mock_bridge: MagicMock) -> None:
        await shader_inspection_operation(
            mock_bridge, "keywords", shader_name="Standard", keyword_filter="global"
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["keywordFilter"] == "global"

    async def test_omits_none_shader_name(self, mock_bridge: MagicMock) -> None:
        """When shader_name is None, shaderName should not be in params."""
        await shader_inspection_operation(mock_bridge, "list")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "shaderName" not in params

    async def test_omits_none_property_name(self, mock_bridge: MagicMock) -> None:
        """When property_name is None, propertyName should not be in params."""
        await shader_inspection_operation(mock_bridge, "list")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "propertyName" not in params

    async def test_custom_timeout(self, mock_bridge: MagicMock) -> None:
        await shader_inspection_operation(mock_bridge, "list", timeout=120.0)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 120.0

    async def test_all_operations_send_correct_type(self, mock_bridge: MagicMock) -> None:
        """Every valid operation must use 'shader-inspection' command type."""
        for op in VALID_OPERATIONS:
            await shader_inspection_operation(
                mock_bridge, op, shader_name="Test/Shader", property_name="_TestProp"
            )
            cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
            assert cmd == "shader-inspection", f"Operation '{op}' used wrong command type: {cmd}"


# ---------------------------------------------------------------------------
# Edge cases and adversarial tests
# ---------------------------------------------------------------------------


class TestShaderEdgeCases:
    async def test_shader_name_empty_string_forwarded(self, mock_bridge: MagicMock) -> None:
        """Empty string is forwarded — C# side handles validation."""
        await shader_info(mock_bridge, "")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["shaderName"] == ""

    async def test_shader_name_with_unicode(self, mock_bridge: MagicMock) -> None:
        """Shader names with unicode characters should pass through."""
        await shader_info(mock_bridge, "Custom/日本語Shader")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["shaderName"] == "Custom/日本語Shader"

    async def test_property_name_with_special_chars(self, mock_bridge: MagicMock) -> None:
        """Property names can contain various characters."""
        await shader_find_by_property(mock_bridge, "_Metallic_GlossMap")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["propertyName"] == "_Metallic_GlossMap"

    async def test_keyword_filter_invalid_value_forwarded(self, mock_bridge: MagicMock) -> None:
        """Invalid filter values are forwarded — C# side handles validation."""
        await shader_keywords(mock_bridge, "Standard", keyword_filter="invalid")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["keywordFilter"] == "invalid"

    async def test_case_sensitive_operation_in_generic(self, mock_bridge: MagicMock) -> None:
        """Mixed case operation should normalize to lowercase."""
        await shader_inspection_operation(mock_bridge, "Find-By-Property", property_name="_Test")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "find-by-property"

    async def test_sql_injection_in_shader_name(self, mock_bridge: MagicMock) -> None:
        """Ensure potentially malicious input is just forwarded as data."""
        name = "'; DROP TABLE shaders; --"
        await shader_info(mock_bridge, name)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["shaderName"] == name

    async def test_very_long_shader_name(self, mock_bridge: MagicMock) -> None:
        """Very long shader names should pass through."""
        name = "A" * 1000
        await shader_info(mock_bridge, name)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["shaderName"] == name

    async def test_concurrent_operations_use_separate_params(self, mock_bridge: MagicMock) -> None:
        """Each call should build independent parameter dicts."""
        await shader_list(mock_bridge, errors_only=True)
        params1 = _extract_parameters(mock_bridge.send_command_with_retry.call_args)

        await shader_list(mock_bridge, errors_only=False)
        params2 = _extract_parameters(mock_bridge.send_command_with_retry.call_args)

        assert params1["errorsOnly"] is True
        assert params2["errorsOnly"] is False


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


class TestShaderSchema:
    def test_schema_has_all_operations(self) -> None:
        """The MCP schema must list all 6 operations."""
        from unity_bridge.mcp.schemas_phase3 import shader_inspection

        schema = shader_inspection()
        ops = schema["properties"]["operation"]["enum"]
        expected = ["list", "info", "errors", "properties", "find-by-property", "keywords"]
        assert ops == expected

    def test_schema_required_fields(self) -> None:
        """Only 'operation' should be required."""
        from unity_bridge.mcp.schemas_phase3 import shader_inspection

        schema = shader_inspection()
        assert schema["required"] == ["operation"]

    def test_schema_has_timeout(self) -> None:
        """Schema must include timeout parameter."""
        from unity_bridge.mcp.schemas_phase3 import shader_inspection

        schema = shader_inspection()
        assert "timeout" in schema["properties"]
        assert schema["properties"]["timeout"]["type"] == "integer"

    def test_schema_has_shader_name(self) -> None:
        from unity_bridge.mcp.schemas_phase3 import shader_inspection

        schema = shader_inspection()
        assert "shaderName" in schema["properties"]

    def test_schema_has_property_name(self) -> None:
        from unity_bridge.mcp.schemas_phase3 import shader_inspection

        schema = shader_inspection()
        assert "propertyName" in schema["properties"]

    def test_schema_has_errors_only(self) -> None:
        from unity_bridge.mcp.schemas_phase3 import shader_inspection

        schema = shader_inspection()
        assert "errorsOnly" in schema["properties"]
        assert schema["properties"]["errorsOnly"]["type"] == "boolean"

    def test_schema_has_keyword_filter(self) -> None:
        from unity_bridge.mcp.schemas_phase3 import shader_inspection

        schema = shader_inspection()
        assert "keywordFilter" in schema["properties"]
        assert schema["properties"]["keywordFilter"]["enum"] == ["global", "local"]

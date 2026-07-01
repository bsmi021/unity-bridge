"""Unit tests for commands/shader.py — shader inspection operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from unity_bridge.core.bridge import CommandResult


def _import_shader():
    from unity_bridge.commands import shader

    return shader


# ---------------------------------------------------------------------------
# list operation
# ---------------------------------------------------------------------------


class TestShaderList:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        await mod.shader_list(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "shader-inspection"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        await mod.shader_list(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "list"
        assert params["errorsOnly"] is False

    async def test_errors_only_flag(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        await mod.shader_list(mock_bridge, errors_only=True)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["errorsOnly"] is True

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        await mod.shader_list(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        timeout = _extract_kwarg(call_args, "timeout")
        assert timeout == 15.0 or timeout == 15

    async def test_custom_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        await mod.shader_list(mock_bridge, timeout=60)
        call_args = mock_bridge.send_command_with_retry.call_args
        timeout = _extract_kwarg(call_args, "timeout")
        assert timeout == 60.0 or timeout == 60

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        expected = CommandResult(
            success=True,
            data={
                "shaders": [{"name": "Standard", "supported": True, "hasErrors": False}],
                "totalCount": 1,
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.shader_list(mock_bridge)
        assert result.success is True
        assert result.data["totalCount"] == 1


# ---------------------------------------------------------------------------
# info operation
# ---------------------------------------------------------------------------


class TestShaderInfo:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        await mod.shader_info(mock_bridge, shader_name="Standard")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "shader-inspection"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        await mod.shader_info(mock_bridge, shader_name="Universal Render Pipeline/Lit")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "info"
        assert params["shaderName"] == "Universal Render Pipeline/Lit"

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        expected = CommandResult(
            success=True,
            data={
                "shaderName": "Standard",
                "supported": True,
                "passCount": 8,
                "propertyCount": 34,
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.shader_info(mock_bridge, shader_name="Standard")
        assert result.success is True
        assert result.data["passCount"] == 8


# ---------------------------------------------------------------------------
# errors operation
# ---------------------------------------------------------------------------


class TestShaderErrors:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        await mod.shader_errors(mock_bridge, shader_name="Custom/Broken")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "shader-inspection"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        await mod.shader_errors(mock_bridge, shader_name="Custom/Broken")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "errors"
        assert params["shaderName"] == "Custom/Broken"

    async def test_empty_messages_response(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        expected = CommandResult(
            success=True,
            data={
                "shaderName": "Standard",
                "hasErrors": False,
                "messages": [],
                "messageCount": 0,
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.shader_errors(mock_bridge, shader_name="Standard")
        assert result.success is True
        assert result.data["messageCount"] == 0
        assert result.data["messages"] == []


# ---------------------------------------------------------------------------
# properties operation
# ---------------------------------------------------------------------------


class TestShaderProperties:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        await mod.shader_properties(mock_bridge, shader_name="Standard")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "shader-inspection"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        await mod.shader_properties(mock_bridge, shader_name="Standard")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "properties"
        assert params["shaderName"] == "Standard"

    async def test_returns_properties_data(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        expected = CommandResult(
            success=True,
            data={
                "shaderName": "Standard",
                "properties": [
                    {
                        "name": "_BaseColor",
                        "type": "Color",
                        "flags": ["MainColor"],
                    },
                    {
                        "name": "_BaseMap",
                        "type": "Texture",
                        "textureDimension": "Tex2D",
                    },
                    {
                        "name": "_Smoothness",
                        "type": "Range",
                        "rangeMin": 0.0,
                        "rangeMax": 1.0,
                    },
                ],
                "propertyCount": 3,
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.shader_properties(mock_bridge, shader_name="Standard")
        assert result.success is True
        assert result.data["propertyCount"] == 3
        assert result.data["properties"][0]["type"] == "Color"
        assert result.data["properties"][1]["type"] == "Texture"
        assert result.data["properties"][2]["type"] == "Range"


# ---------------------------------------------------------------------------
# find-by-property operation
# ---------------------------------------------------------------------------


class TestShaderFindByProperty:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        await mod.shader_find_by_property(mock_bridge, property_name="_MainTex")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "shader-inspection"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        await mod.shader_find_by_property(mock_bridge, property_name="_MainTex")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "find-by-property"
        assert params["propertyName"] == "_MainTex"

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        expected = CommandResult(
            success=True,
            data={
                "propertyName": "_MainTex",
                "shaders": [
                    {"name": "Standard", "propertyType": "Texture"},
                    {"name": "Unlit/Texture", "propertyType": "Texture"},
                ],
                "matchCount": 2,
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.shader_find_by_property(mock_bridge, property_name="_MainTex")
        assert result.success is True
        assert result.data["matchCount"] == 2


# ---------------------------------------------------------------------------
# keywords operation
# ---------------------------------------------------------------------------


class TestShaderKeywords:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        await mod.shader_keywords(mock_bridge, shader_name="Standard")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "shader-inspection"

    async def test_sends_correct_parameters_no_filter(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        await mod.shader_keywords(mock_bridge, shader_name="Standard")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "keywords"
        assert params["shaderName"] == "Standard"
        assert "keywordFilter" not in params

    async def test_sends_global_filter(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        await mod.shader_keywords(mock_bridge, shader_name="Standard", keyword_filter="global")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["keywordFilter"] == "global"

    async def test_sends_local_filter(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        await mod.shader_keywords(mock_bridge, shader_name="Standard", keyword_filter="local")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["keywordFilter"] == "local"

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        expected = CommandResult(
            success=True,
            data={
                "shaderName": "Standard",
                "globalKeywords": ["_MAIN_LIGHT_SHADOWS"],
                "localKeywords": ["_NORMALMAP", "_EMISSION"],
                "globalCount": 1,
                "localCount": 2,
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.shader_keywords(mock_bridge, shader_name="Standard")
        assert result.success is True
        assert result.data["globalCount"] == 1
        assert result.data["localCount"] == 2


# ---------------------------------------------------------------------------
# Generic operation function
# ---------------------------------------------------------------------------


class TestGenericOperation:
    async def test_list_via_generic(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        await mod.shader_inspection_operation(mock_bridge, operation="list")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "list"

    async def test_info_via_generic(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        await mod.shader_inspection_operation(mock_bridge, operation="info", shader_name="Standard")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "info"
        assert params["shaderName"] == "Standard"

    async def test_find_by_property_via_generic(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        await mod.shader_inspection_operation(
            mock_bridge, operation="find-by-property", property_name="_MainTex"
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "find-by-property"
        assert params["propertyName"] == "_MainTex"

    async def test_keywords_via_generic(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        await mod.shader_inspection_operation(
            mock_bridge,
            operation="keywords",
            shader_name="Standard",
            keyword_filter="global",
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "keywords"
        assert params["keywordFilter"] == "global"

    async def test_errors_only_via_generic(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        await mod.shader_inspection_operation(mock_bridge, operation="list", errors_only=True)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["errorsOnly"] is True

    async def test_optional_params_excluded(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        await mod.shader_inspection_operation(mock_bridge, operation="list")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert "shaderName" not in params
        assert "propertyName" not in params
        assert "keywordFilter" not in params
        # errorsOnly defaults to False, so not included when False
        assert params.get("errorsOnly") is None or params.get("errorsOnly") is False


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    async def test_invalid_operation_raises(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        with pytest.raises(ValueError, match="Invalid shader inspection operation"):
            await mod.shader_inspection_operation(mock_bridge, operation="invalid")

    async def test_operation_normalised(self, mock_bridge: MagicMock) -> None:
        mod = _import_shader()
        await mod.shader_inspection_operation(mock_bridge, operation="  LIST  ")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "list"


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class TestProtocol:
    def test_timeout_default_in_protocol(self) -> None:
        from unity_bridge.core.protocol import TIMEOUT_DEFAULTS

        assert "shader-inspection" in TIMEOUT_DEFAULTS
        assert TIMEOUT_DEFAULTS["shader-inspection"] == 15

    def test_is_parallel_safe(self) -> None:
        from unity_bridge.core.protocol import PARALLEL_SAFE_COMMANDS

        assert "shader-inspection" in PARALLEL_SAFE_COMMANDS


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

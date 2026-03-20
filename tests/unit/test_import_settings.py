"""Unit tests for commands/import_settings.py — import settings operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from unity_bridge.core.bridge import CommandResult


def _import_mod():
    from unity_bridge.commands import import_settings

    return import_settings


# ---------------------------------------------------------------------------
# get operation
# ---------------------------------------------------------------------------


class TestImportSettingsGet:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.import_settings_get(mock_bridge, asset_path="Assets/Tex/A.png")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "import-settings-operation"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.import_settings_get(mock_bridge, asset_path="Assets/Tex/A.png")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "get"
        assert params["assetPath"] == "Assets/Tex/A.png"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.import_settings_get(mock_bridge, asset_path="Assets/Tex/A.png")
        call_args = mock_bridge.send_command_with_retry.call_args
        timeout = _extract_kwarg(call_args, "timeout")
        assert timeout == 60.0 or timeout == 60

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        expected = CommandResult(
            success=True,
            data={
                "importerType": "TextureImporter",
                "settings": {"maxTextureSize": "2048"},
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.import_settings_get(mock_bridge, asset_path="Assets/Tex/A.png")
        assert result.success is True
        assert result.data["importerType"] == "TextureImporter"


# ---------------------------------------------------------------------------
# set operation
# ---------------------------------------------------------------------------


class TestImportSettingsSet:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.import_settings_set(
            mock_bridge, asset_path="Assets/Tex/A.png", settings={"maxTextureSize": "1024"}
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "import-settings-operation"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        settings = {"maxTextureSize": "1024", "mipmapEnabled": "false"}
        await mod.import_settings_set(mock_bridge, asset_path="Assets/Tex/A.png", settings=settings)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "set"
        assert params["assetPath"] == "Assets/Tex/A.png"
        assert params["settings"] == settings

    async def test_empty_settings_raises(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        with pytest.raises(ValueError, match="At least one setting"):
            await mod.import_settings_set(mock_bridge, asset_path="Assets/Tex/A.png", settings={})

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        expected = CommandResult(
            success=True,
            data={"updatedSettings": ["maxTextureSize"], "updatedCount": 1, "reimported": True},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.import_settings_set(
            mock_bridge, asset_path="Assets/Tex/A.png", settings={"maxTextureSize": "1024"}
        )
        assert result.success is True
        assert result.data["reimported"] is True


# ---------------------------------------------------------------------------
# reimport operation
# ---------------------------------------------------------------------------


class TestImportSettingsReimport:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.import_settings_reimport(mock_bridge, asset_path="Assets/Tex/A.png")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "reimport"
        assert params["assetPath"] == "Assets/Tex/A.png"
        assert "force" not in params

    async def test_force_flag(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.import_settings_reimport(mock_bridge, asset_path="Assets/Tex/A.png", force=True)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["force"] is True


# ---------------------------------------------------------------------------
# bulk-set operation
# ---------------------------------------------------------------------------


class TestImportSettingsBulkSet:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.import_settings_bulk_set(
            mock_bridge,
            folder_path="Assets/Textures",
            settings={"maxTextureSize": "1024"},
            filter_pattern="*.png",
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "bulk-set"
        assert params["folderPath"] == "Assets/Textures"
        assert params["settings"] == {"maxTextureSize": "1024"}
        assert params["filter"] == "*.png"

    async def test_optional_filter_excluded(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.import_settings_bulk_set(
            mock_bridge,
            folder_path="Assets/Textures",
            settings={"maxTextureSize": "1024"},
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert "filter" not in params

    async def test_empty_settings_raises(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        with pytest.raises(ValueError, match="At least one setting"):
            await mod.import_settings_bulk_set(
                mock_bridge, folder_path="Assets/Textures", settings={}
            )


# ---------------------------------------------------------------------------
# template-save operation
# ---------------------------------------------------------------------------


class TestImportSettingsTemplateSave:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.import_settings_template_save(
            mock_bridge, template_name="my-template", asset_path="Assets/Tex/A.png"
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "template-save"
        assert params["templateName"] == "my-template"
        assert params["assetPath"] == "Assets/Tex/A.png"

    async def test_invalid_template_name_raises(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        with pytest.raises(ValueError, match="Invalid template name"):
            await mod.import_settings_template_save(
                mock_bridge, template_name="bad name!!", asset_path="Assets/Tex/A.png"
            )

    async def test_empty_template_name_raises(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        with pytest.raises(ValueError, match="Invalid template name"):
            await mod.import_settings_template_save(
                mock_bridge, template_name="", asset_path="Assets/Tex/A.png"
            )

    async def test_too_long_template_name_raises(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        with pytest.raises(ValueError, match="Invalid template name"):
            await mod.import_settings_template_save(
                mock_bridge, template_name="a" * 65, asset_path="Assets/Tex/A.png"
            )

    async def test_valid_template_names(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        for name in ["char-tex-2k", "my_template", "Template123", "a-b_c"]:
            await mod.import_settings_template_save(
                mock_bridge, template_name=name, asset_path="Assets/Tex/A.png"
            )


# ---------------------------------------------------------------------------
# template-apply operation
# ---------------------------------------------------------------------------


class TestImportSettingsTemplateApply:
    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.import_settings_template_apply(
            mock_bridge, template_name="my-template", asset_path="Assets/Tex/B.png"
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "template-apply"
        assert params["templateName"] == "my-template"
        assert params["assetPath"] == "Assets/Tex/B.png"

    async def test_handles_type_mismatch_response(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        expected = CommandResult(
            success=False,
            error="Template type mismatch: template is TextureImporter but asset uses ModelImporter",
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.import_settings_template_apply(
            mock_bridge, template_name="tex-template", asset_path="Assets/Models/Char.fbx"
        )
        assert result.success is False
        assert "mismatch" in (result.error or "")


# ---------------------------------------------------------------------------
# Generic operation function
# ---------------------------------------------------------------------------


class TestGenericOperation:
    async def test_get_via_generic(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.import_settings_operation(
            mock_bridge, operation="get", asset_path="Assets/Tex/A.png"
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "get"
        assert params["assetPath"] == "Assets/Tex/A.png"

    async def test_set_via_generic(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.import_settings_operation(
            mock_bridge,
            operation="set",
            asset_path="Assets/Tex/A.png",
            settings={"maxTextureSize": "1024"},
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "set"
        assert params["settings"] == {"maxTextureSize": "1024"}

    async def test_bulk_set_via_generic(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.import_settings_operation(
            mock_bridge,
            operation="bulk-set",
            folder_path="Assets/Textures",
            settings={"maxTextureSize": "1024"},
            filter_pattern="*.png",
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "bulk-set"
        assert params["folderPath"] == "Assets/Textures"
        assert params["filter"] == "*.png"

    async def test_optional_params_excluded(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.import_settings_operation(mock_bridge, operation="get")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert "assetPath" not in params
        assert "settings" not in params
        assert "templateName" not in params
        assert "folderPath" not in params
        assert "filter" not in params
        assert "force" not in params


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    async def test_invalid_operation_raises(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        with pytest.raises(ValueError, match="Invalid import settings operation"):
            await mod.import_settings_operation(mock_bridge, operation="invalid")

    async def test_operation_normalised(self, mock_bridge: MagicMock) -> None:
        mod = _import_mod()
        await mod.import_settings_operation(mock_bridge, operation="  GET  ")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "get"


# ---------------------------------------------------------------------------
# MCP schema
# ---------------------------------------------------------------------------


class TestSchema:
    def test_import_settings_schema_structure(self) -> None:
        from unity_bridge.mcp.schemas_phase3 import import_settings

        schema = import_settings()
        assert schema["type"] == "object"
        assert "operation" in schema["properties"]
        assert schema["required"] == ["operation"]

    def test_import_settings_schema_operations(self) -> None:
        from unity_bridge.mcp.schemas_phase3 import import_settings

        schema = import_settings()
        ops = schema["properties"]["operation"]["enum"]
        assert set(ops) == {
            "get",
            "set",
            "reimport",
            "bulk-set",
            "template-save",
            "template-apply",
        }

    def test_import_settings_schema_has_timeout(self) -> None:
        from unity_bridge.mcp.schemas_phase3 import import_settings

        schema = import_settings()
        assert "timeout" in schema["properties"]

    def test_import_settings_schema_has_asset_path(self) -> None:
        from unity_bridge.mcp.schemas_phase3 import import_settings

        schema = import_settings()
        assert "assetPath" in schema["properties"]

    def test_import_settings_schema_has_settings(self) -> None:
        from unity_bridge.mcp.schemas_phase3 import import_settings

        schema = import_settings()
        assert "settings" in schema["properties"]

    def test_import_settings_schema_has_template_name(self) -> None:
        from unity_bridge.mcp.schemas_phase3 import import_settings

        schema = import_settings()
        assert "templateName" in schema["properties"]

    def test_import_settings_schema_has_folder_path(self) -> None:
        from unity_bridge.mcp.schemas_phase3 import import_settings

        schema = import_settings()
        assert "folderPath" in schema["properties"]


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


class TestToolRegistration:
    def test_tool_in_command_map(self) -> None:
        from unity_bridge.mcp.tools import TOOL_COMMAND_MAP

        assert "unity_import_settings" in TOOL_COMMAND_MAP
        assert TOOL_COMMAND_MAP["unity_import_settings"] == "import-settings-operation"

    def test_tool_in_definitions(self) -> None:
        from unity_bridge.mcp.tools import TOOL_DEFINITIONS

        names = [t["name"] for t in TOOL_DEFINITIONS]
        assert "unity_import_settings" in names


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class TestProtocol:
    def test_timeout_default_in_protocol(self) -> None:
        from unity_bridge.core.protocol import TIMEOUT_DEFAULTS

        assert "import-settings-operation" in TIMEOUT_DEFAULTS
        assert TIMEOUT_DEFAULTS["import-settings-operation"] == 60

    def test_not_parallel_safe(self) -> None:
        from unity_bridge.core.protocol import PARALLEL_SAFE_COMMANDS

        assert "import-settings-operation" not in PARALLEL_SAFE_COMMANDS


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

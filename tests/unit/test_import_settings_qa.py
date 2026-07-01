"""Adversarial QA tests for commands/import_settings.py — edge cases and spec compliance.

Covers:
- Template name validation edge cases (path traversal, injection, unicode, length)
- Operation validation and normalisation
- Empty settings rejection for set / bulk-set
- Correct command type (import-settings-operation)
- Parameter forwarding for all 6 operations
- Generic dispatch includes/excludes optional params correctly
- Schema enum matches VALID_OPERATIONS
- Timeout defaults (protocol + function-level)
- Force flag conditional inclusion
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from unity_bridge.commands.import_settings import (
    VALID_OPERATIONS,
    _validate_template_name,
    import_settings_bulk_set,
    import_settings_get,
    import_settings_operation,
    import_settings_reimport,
    import_settings_set,
    import_settings_template_apply,
    import_settings_template_save,
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
# Template name validation edge cases
# ---------------------------------------------------------------------------


class TestTemplateNameValidation:
    def test_valid_alphanumeric(self) -> None:
        _validate_template_name("mytemplate123")

    def test_valid_hyphens(self) -> None:
        _validate_template_name("my-template")

    def test_valid_underscores(self) -> None:
        _validate_template_name("my_template")

    def test_valid_mixed(self) -> None:
        _validate_template_name("char-tex_2k")

    def test_valid_max_length(self) -> None:
        _validate_template_name("a" * 64)

    def test_invalid_too_long(self) -> None:
        with pytest.raises(ValueError, match="Invalid template name"):
            _validate_template_name("a" * 65)

    def test_invalid_empty(self) -> None:
        with pytest.raises(ValueError, match="Invalid template name"):
            _validate_template_name("")

    def test_invalid_spaces(self) -> None:
        with pytest.raises(ValueError, match="Invalid template name"):
            _validate_template_name("my template")

    def test_invalid_dots(self) -> None:
        with pytest.raises(ValueError, match="Invalid template name"):
            _validate_template_name("my.template")

    def test_invalid_path_traversal(self) -> None:
        with pytest.raises(ValueError, match="Invalid template name"):
            _validate_template_name("../../../etc/passwd")

    def test_invalid_shell_injection(self) -> None:
        with pytest.raises(ValueError, match="Invalid template name"):
            _validate_template_name("; rm -rf /")

    def test_invalid_unicode(self) -> None:
        with pytest.raises(ValueError, match="Invalid template name"):
            _validate_template_name("template_日本語")

    def test_invalid_null_bytes(self) -> None:
        with pytest.raises(ValueError, match="Invalid template name"):
            _validate_template_name("template\x00evil")

    def test_invalid_slashes(self) -> None:
        with pytest.raises(ValueError, match="Invalid template name"):
            _validate_template_name("path/to/template")

    def test_invalid_backslashes(self) -> None:
        with pytest.raises(ValueError, match="Invalid template name"):
            _validate_template_name("path\\to\\template")


# ---------------------------------------------------------------------------
# All operations use import-settings-operation command type
# ---------------------------------------------------------------------------


class TestCommandTypeConsistency:
    """All import settings functions must use 'import-settings-operation'."""

    async def test_get_command_type(self, mock_bridge: MagicMock) -> None:
        await import_settings_get(mock_bridge, asset_path="Assets/Tex/A.png")
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "import-settings-operation"

    async def test_set_command_type(self, mock_bridge: MagicMock) -> None:
        await import_settings_set(mock_bridge, asset_path="Assets/Tex/A.png", settings={"k": "v"})
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "import-settings-operation"

    async def test_reimport_command_type(self, mock_bridge: MagicMock) -> None:
        await import_settings_reimport(mock_bridge, asset_path="Assets/Tex/A.png")
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "import-settings-operation"

    async def test_bulk_set_command_type(self, mock_bridge: MagicMock) -> None:
        await import_settings_bulk_set(
            mock_bridge, folder_path="Assets/Textures", settings={"k": "v"}
        )
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "import-settings-operation"

    async def test_template_save_command_type(self, mock_bridge: MagicMock) -> None:
        await import_settings_template_save(
            mock_bridge, template_name="my-tmpl", asset_path="Assets/Tex/A.png"
        )
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "import-settings-operation"

    async def test_template_apply_command_type(self, mock_bridge: MagicMock) -> None:
        await import_settings_template_apply(
            mock_bridge, template_name="my-tmpl", asset_path="Assets/Tex/A.png"
        )
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "import-settings-operation"


# ---------------------------------------------------------------------------
# Empty settings rejection
# ---------------------------------------------------------------------------


class TestEmptySettingsRejection:
    """set and bulk-set must reject empty settings dicts."""

    async def test_set_empty_settings(self, mock_bridge: MagicMock) -> None:
        with pytest.raises(ValueError, match="At least one setting"):
            await import_settings_set(mock_bridge, asset_path="Assets/Tex/A.png", settings={})

    async def test_bulk_set_empty_settings(self, mock_bridge: MagicMock) -> None:
        with pytest.raises(ValueError, match="At least one setting"):
            await import_settings_bulk_set(mock_bridge, folder_path="Assets/Textures", settings={})

    async def test_set_does_not_send_to_bridge(self, mock_bridge: MagicMock) -> None:
        """Bridge should NOT be called when validation fails."""
        with pytest.raises(ValueError):
            await import_settings_set(mock_bridge, asset_path="Assets/Tex/A.png", settings={})
        mock_bridge.send_command_with_retry.assert_not_called()


# ---------------------------------------------------------------------------
# Operation validation via generic dispatch
# ---------------------------------------------------------------------------


class TestOperationValidation:
    async def test_invalid_operation_raises(self, mock_bridge: MagicMock) -> None:
        with pytest.raises(ValueError, match="Invalid import settings operation"):
            await import_settings_operation(mock_bridge, operation="delete")

    async def test_empty_operation_raises(self, mock_bridge: MagicMock) -> None:
        with pytest.raises(ValueError, match="Invalid import settings operation"):
            await import_settings_operation(mock_bridge, operation="")

    async def test_operation_case_normalised(self, mock_bridge: MagicMock) -> None:
        await import_settings_operation(mock_bridge, operation="  GET  ")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "get"

    async def test_operation_strip_whitespace(self, mock_bridge: MagicMock) -> None:
        await import_settings_operation(mock_bridge, operation="\treimport\n")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "reimport"

    async def test_all_valid_operations_accepted(self, mock_bridge: MagicMock) -> None:
        for op in VALID_OPERATIONS:
            await import_settings_operation(mock_bridge, operation=op)


# ---------------------------------------------------------------------------
# VALID_OPERATIONS matches schema
# ---------------------------------------------------------------------------


class TestOperationsMatchSchema:
    def test_valid_operations_count(self) -> None:
        assert len(VALID_OPERATIONS) == 6

    def test_expected_operations_present(self) -> None:
        expected = {"get", "set", "reimport", "bulk-set", "template-save", "template-apply"}
        assert VALID_OPERATIONS == expected


# ---------------------------------------------------------------------------
# Timeout defaults
# ---------------------------------------------------------------------------


class TestTimeoutDefaults:
    async def test_get_default_timeout(self, mock_bridge: MagicMock) -> None:
        await import_settings_get(mock_bridge, asset_path="Assets/Tex/A.png")
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 60.0

    async def test_set_default_timeout(self, mock_bridge: MagicMock) -> None:
        await import_settings_set(mock_bridge, asset_path="Assets/Tex/A.png", settings={"k": "v"})
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 60.0

    async def test_custom_timeout_forwarded(self, mock_bridge: MagicMock) -> None:
        await import_settings_get(mock_bridge, asset_path="Assets/Tex/A.png", timeout=120.0)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 120.0

    def test_protocol_timeout_matches(self) -> None:
        from unity_bridge.core.protocol import TIMEOUT_DEFAULTS

        assert TIMEOUT_DEFAULTS["import-settings-operation"] == 60


# ---------------------------------------------------------------------------
# Force flag conditional inclusion
# ---------------------------------------------------------------------------


class TestForceFlag:
    async def test_reimport_no_force_by_default(self, mock_bridge: MagicMock) -> None:
        await import_settings_reimport(mock_bridge, asset_path="Assets/Tex/A.png")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "force" not in params

    async def test_reimport_force_true(self, mock_bridge: MagicMock) -> None:
        await import_settings_reimport(mock_bridge, asset_path="Assets/Tex/A.png", force=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["force"] is True

    async def test_reimport_force_false_excluded(self, mock_bridge: MagicMock) -> None:
        """force=False should NOT be sent — only include when True."""
        await import_settings_reimport(mock_bridge, asset_path="Assets/Tex/A.png", force=False)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "force" not in params

    async def test_generic_force_true(self, mock_bridge: MagicMock) -> None:
        await import_settings_operation(mock_bridge, operation="reimport", force=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["force"] is True

    async def test_generic_force_false_excluded(self, mock_bridge: MagicMock) -> None:
        await import_settings_operation(mock_bridge, operation="reimport", force=False)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "force" not in params


# ---------------------------------------------------------------------------
# Bulk-set filter parameter
# ---------------------------------------------------------------------------


class TestBulkSetFilter:
    async def test_filter_included_when_provided(self, mock_bridge: MagicMock) -> None:
        await import_settings_bulk_set(
            mock_bridge,
            folder_path="Assets/Textures",
            settings={"maxTextureSize": "1024"},
            filter_pattern="*.png",
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["filter"] == "*.png"

    async def test_filter_excluded_when_none(self, mock_bridge: MagicMock) -> None:
        await import_settings_bulk_set(
            mock_bridge,
            folder_path="Assets/Textures",
            settings={"maxTextureSize": "1024"},
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "filter" not in params

    async def test_filter_via_generic(self, mock_bridge: MagicMock) -> None:
        await import_settings_operation(
            mock_bridge,
            operation="bulk-set",
            folder_path="Assets/Textures",
            settings={"maxTextureSize": "1024"},
            filter_pattern="*.fbx",
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["filter"] == "*.fbx"


# ---------------------------------------------------------------------------
# Template save validates name, template apply does not
# ---------------------------------------------------------------------------


class TestTemplateSaveApplyAsymmetry:
    """template-save validates name Python-side; template-apply does not."""

    async def test_save_rejects_invalid_name(self, mock_bridge: MagicMock) -> None:
        with pytest.raises(ValueError, match="Invalid template name"):
            await import_settings_template_save(
                mock_bridge, template_name="bad name!", asset_path="Assets/Tex/A.png"
            )

    async def test_apply_accepts_any_name(self, mock_bridge: MagicMock) -> None:
        """template-apply does NOT validate — C# side validates existence."""
        await import_settings_template_apply(
            mock_bridge, template_name="any-name", asset_path="Assets/Tex/A.png"
        )
        mock_bridge.send_command_with_retry.assert_called_once()

    async def test_save_invalid_does_not_call_bridge(self, mock_bridge: MagicMock) -> None:
        with pytest.raises(ValueError):
            await import_settings_template_save(
                mock_bridge, template_name="", asset_path="Assets/Tex/A.png"
            )
        mock_bridge.send_command_with_retry.assert_not_called()


# ---------------------------------------------------------------------------
# Generic dispatch optional params exclusion
# ---------------------------------------------------------------------------


class TestGenericDispatchOptionalParams:
    async def test_get_excludes_all_optional(self, mock_bridge: MagicMock) -> None:
        await import_settings_operation(mock_bridge, operation="get")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "get"}
        for key in ["assetPath", "settings", "templateName", "folderPath", "filter", "force"]:
            assert key not in params

    async def test_set_includes_asset_path_and_settings(self, mock_bridge: MagicMock) -> None:
        await import_settings_operation(
            mock_bridge,
            operation="set",
            asset_path="Assets/Tex/A.png",
            settings={"k": "v"},
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["assetPath"] == "Assets/Tex/A.png"
        assert params["settings"] == {"k": "v"}
        assert "templateName" not in params
        assert "folderPath" not in params

    async def test_template_save_includes_template_name(self, mock_bridge: MagicMock) -> None:
        await import_settings_operation(
            mock_bridge,
            operation="template-save",
            template_name="my-tmpl",
            asset_path="Assets/Tex/A.png",
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["templateName"] == "my-tmpl"
        assert params["assetPath"] == "Assets/Tex/A.png"


# ---------------------------------------------------------------------------
# Error response handling
# ---------------------------------------------------------------------------


class TestErrorResponseHandling:
    async def test_asset_not_found_propagated(self, mock_bridge: MagicMock) -> None:
        error_result = CommandResult(
            success=False, data=None, error="Asset not found or no importer: Assets/Nope.png"
        )
        mock_bridge.send_command_with_retry.return_value = error_result
        result = await import_settings_get(mock_bridge, asset_path="Assets/Nope.png")
        assert result.success is False
        assert "not found" in (result.error or "")

    async def test_template_type_mismatch_propagated(self, mock_bridge: MagicMock) -> None:
        error_result = CommandResult(
            success=False,
            error="Template type mismatch: template is TextureImporter but asset uses ModelImporter",
        )
        mock_bridge.send_command_with_retry.return_value = error_result
        result = await import_settings_template_apply(
            mock_bridge, template_name="tex-tmpl", asset_path="Assets/Models/Char.fbx"
        )
        assert result.success is False
        assert "mismatch" in (result.error or "")

    async def test_template_not_found_propagated(self, mock_bridge: MagicMock) -> None:
        error_result = CommandResult(success=False, error="Template not found: nonexistent")
        mock_bridge.send_command_with_retry.return_value = error_result
        result = await import_settings_template_apply(
            mock_bridge, template_name="nonexistent", asset_path="Assets/Tex/A.png"
        )
        assert result.success is False

    async def test_play_mode_error_propagated(self, mock_bridge: MagicMock) -> None:
        error_result = CommandResult(
            success=False, error="Cannot modify import settings during play mode."
        )
        mock_bridge.send_command_with_retry.return_value = error_result
        result = await import_settings_set(
            mock_bridge, asset_path="Assets/Tex/A.png", settings={"k": "v"}
        )
        assert result.success is False


# ---------------------------------------------------------------------------
# Not parallel safe
# ---------------------------------------------------------------------------


class TestParallelSafety:
    def test_import_settings_not_parallel_safe(self) -> None:
        from unity_bridge.core.protocol import PARALLEL_SAFE_COMMANDS

        assert "import-settings-operation" not in PARALLEL_SAFE_COMMANDS

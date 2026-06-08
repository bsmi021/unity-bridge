"""Unit tests for Phase 2 authoring-system bridge surfaces."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from unity_bridge.commands import addressables, input_system, ui_toolkit

ROOT = Path(__file__).resolve().parents[2]


def _call_args(mock: MagicMock) -> dict[str, Any]:
    call = mock.send_command_with_retry.call_args
    return call.kwargs if call.kwargs else dict(
        zip(["command_type", "parameters", "timeout"], call.args, strict=False)
    )


class TestUIToolkitCommands:
    async def test_list_documents_dispatches(self, mock_bridge: MagicMock) -> None:
        await ui_toolkit.ui_list_documents(mock_bridge)

        assert _call_args(mock_bridge)["parameters"] == {"operation": "list-documents"}
        assert _call_args(mock_bridge)["command_type"] == "ui-toolkit"

    async def test_add_ui_document_dispatches_optional_fields(
        self, mock_bridge: MagicMock
    ) -> None:
        await ui_toolkit.ui_add_document(
            mock_bridge,
            game_object_path="Canvas",
            uxml_path="Assets/UI/Hud.uxml",
            panel_settings_path="Assets/UI/Panel.asset",
            sorting_order=5,
        )

        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "add-ui-document",
            "gameObjectPath": "Canvas",
            "uxmlPath": "Assets/UI/Hud.uxml",
            "panelSettingsPath": "Assets/UI/Panel.asset",
            "sortingOrder": 5,
        }


class TestInputSystemAuthoring:
    async def test_create_asset_dispatches(self, mock_bridge: MagicMock) -> None:
        await input_system.input_create_asset(
            mock_bridge,
            "Assets/Input/Game.inputactions",
            overwrite=True,
        )

        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "create-asset",
            "assetPath": "Assets/Input/Game.inputactions",
            "overwrite": True,
        }

    async def test_add_binding_dispatches(self, mock_bridge: MagicMock) -> None:
        await input_system.input_add_binding(
            mock_bridge,
            "Assets/Input/Game.inputactions",
            action_map="Player",
            action_name="Jump",
            binding_path="<Keyboard>/space",
            groups="Keyboard&Mouse",
        )

        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "add-binding",
            "assetPath": "Assets/Input/Game.inputactions",
            "actionMap": "Player",
            "actionName": "Jump",
            "bindingPath": "<Keyboard>/space",
            "groups": "Keyboard&Mouse",
        }

    async def test_add_action_map_dispatches_overwrite(
        self, mock_bridge: MagicMock
    ) -> None:
        await input_system.input_add_action_map(
            mock_bridge,
            "Assets/Input/Game.inputactions",
            "Player",
            overwrite=True,
        )

        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "add-action-map",
            "assetPath": "Assets/Input/Game.inputactions",
            "actionMap": "Player",
            "overwrite": True,
        }

    async def test_add_action_dispatches_overwrite(self, mock_bridge: MagicMock) -> None:
        await input_system.input_add_action(
            mock_bridge,
            "Assets/Input/Game.inputactions",
            action_map="Player",
            action_name="Jump",
            overwrite=True,
        )

        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "add-action",
            "assetPath": "Assets/Input/Game.inputactions",
            "actionMap": "Player",
            "actionName": "Jump",
            "overwrite": True,
        }

    async def test_add_control_scheme_dispatches(
        self, mock_bridge: MagicMock
    ) -> None:
        await input_system.input_add_control_scheme(
            mock_bridge,
            "Assets/Input/Game.inputactions",
            control_scheme="Gamepad",
            binding_group="Gamepad",
            device_paths=["<Gamepad>"],
        )

        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "add-control-scheme",
            "assetPath": "Assets/Input/Game.inputactions",
            "controlScheme": "Gamepad",
            "bindingGroup": "Gamepad",
            "devicePaths": ["<Gamepad>"],
        }

    async def test_add_control_scheme_allows_optional_details(
        self, mock_bridge: MagicMock
    ) -> None:
        await input_system.input_add_control_scheme(
            mock_bridge,
            "Assets/Input/Game.inputactions",
            control_scheme="Keyboard&Mouse",
        )

        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "add-control-scheme",
            "assetPath": "Assets/Input/Game.inputactions",
            "controlScheme": "Keyboard&Mouse",
        }

    async def test_add_control_scheme_dispatches_overwrite(
        self, mock_bridge: MagicMock
    ) -> None:
        await input_system.input_add_control_scheme(
            mock_bridge,
            "Assets/Input/Game.inputactions",
            control_scheme="Gamepad",
            binding_group="Gamepad",
            device_paths=["<Gamepad>"],
            overwrite=True,
        )

        assert _call_args(mock_bridge)["parameters"]["overwrite"] is True

    def test_csharp_control_scheme_optional_details_are_not_rejected(self) -> None:
        source = (ROOT / "ClaudeCodeBridge" / "InputSystemAuthoringHelpers.cs").read_text(
            encoding="utf-8"
        )

        assert 'Require(p.controlScheme, "controlScheme")' in source
        assert "if (!string.IsNullOrEmpty(p.bindingGroup))" in source
        assert 'Require(p.bindingGroup, "bindingGroup")' not in source
        assert "devicePaths is required" not in source


class TestAddressablesAdvanced:
    async def test_list_profiles_dispatches(self, mock_bridge: MagicMock) -> None:
        await addressables.addressables_list_profiles(mock_bridge)

        assert _call_args(mock_bridge)["parameters"] == {"operation": "list-profiles"}

    async def test_set_label_dispatches(self, mock_bridge: MagicMock) -> None:
        await addressables.addressables_set_label(
            mock_bridge,
            "Assets/Prefabs/Player.prefab",
            label="characters",
            enable=False,
            force=True,
        )

        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "set-label",
            "assetPath": "Assets/Prefabs/Player.prefab",
            "label": "characters",
            "enable": False,
            "force": True,
        }

    async def test_analyze_dispatches(self, mock_bridge: MagicMock) -> None:
        await addressables.addressables_analyze(
            mock_bridge,
            analyze_rule="Check Duplicate Bundle Dependencies",
            output_path="Temp/addressables-analyze.json",
        )

        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "analyze",
            "analyzeRule": "Check Duplicate Bundle Dependencies",
            "outputPath": "Temp/addressables-analyze.json",
        }


class TestAuthoringMcpAndProtocol:
    def test_tool_map_entries(self) -> None:
        from unity_bridge.mcp.tools import TOOL_COMMAND_MAP

        assert TOOL_COMMAND_MAP["unity_ui_toolkit"] == "ui-toolkit"
        assert TOOL_COMMAND_MAP["unity_input_system"] == "input-system"
        assert TOOL_COMMAND_MAP["unity_addressables"] == "addressables"

    def test_timeout_defaults(self) -> None:
        from unity_bridge.core.protocol import TIMEOUT_DEFAULTS

        assert TIMEOUT_DEFAULTS["ui-toolkit"] == 15
        assert TIMEOUT_DEFAULTS["input-system"] == 30
        assert TIMEOUT_DEFAULTS["addressables"] == 300

    def test_schemas_include_new_operations(self) -> None:
        from unity_bridge.mcp import schemas_authoring, schemas_phase4_ext, schemas_phase4_misc

        ui_ops = schemas_authoring.ui_toolkit()["properties"]["operation"]["enum"]
        input_ops = schemas_phase4_misc.input_system()["properties"]["operation"]["enum"]
        addr_ops = schemas_phase4_ext.addressables_operation()["properties"]["operation"]["enum"]
        assert "add-ui-document" in ui_ops
        assert "add-binding" in input_ops
        assert "set-label" in addr_ops

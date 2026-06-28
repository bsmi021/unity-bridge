"""Integration tests for MCP tool definition compatibility."""

from __future__ import annotations

import pytest

from unity_bridge.mcp.tools import TOOL_COMMAND_MAP, TOOL_DEFINITIONS

pytestmark = pytest.mark.integration


EXPECTED_TOOL_NAMES = {
    "unity_run_tests",
    "unity_query_hierarchy",
    "unity_get_component_data",
    "unity_set_component_data",
    "unity_add_component",
    "unity_validate_prefab",
    "unity_scene_operation",
    "unity_prefab_operation",
    "unity_playmode_control",
    "unity_read_console",
    "unity_capture_screenshot",
    "unity_profiler_sample",
    "unity_material_operation",
    "unity_asset_operation",
    "unity_build_operation",
    "unity_animator_operation",
    "unity_bridge_config",
    "unity_clear_console",
    "unity_get_selection",
    "unity_refresh_assets",
    "unity_focus_object",
    "unity_health_check",
    "unity_compile",
    "unity_execute_menu_item",
    "unity_batch",
    "unity_help",
}

EXPECTED_TOOL_MAP = {
    "unity_run_tests": "run-tests",
    "unity_query_hierarchy": "query-hierarchy",
    "unity_get_component_data": "get-component-data",
    "unity_set_component_data": "set-component-data",
    "unity_add_component": "add-component",
    "unity_validate_prefab": "validate-prefab",
    "unity_scene_operation": "scene-operation",
    "unity_prefab_operation": "prefab-operation",
    "unity_playmode_control": "playmode-control",
    "unity_read_console": "read-console",
    "unity_capture_screenshot": "capture-screenshot",
    "unity_profiler_sample": "profiler-sample",
    "unity_material_operation": "material-operation",
    "unity_asset_operation": "asset-operation",
    "unity_build_operation": "build-operation",
    "unity_animator_operation": "animator-operation",
    "unity_clear_console": "clear-console",
    "unity_get_selection": "get-selection",
    "unity_refresh_assets": "refresh-assets",
    "unity_focus_object": "focus-object",
    "unity_compile": "compile",
    "unity_execute_menu_item": "execute-menu-item",
}

EXPECTED_CURRENT_SURFACE = {
    "unity_navmesh",
    "unity_animation_clip",
    "unity_terrain",
    "unity_reflection_probe",
    "unity_occlusion_culling",
    "unity_addressables",
    "unity_tilemap",
    "unity_clipboard",
    "unity_preset",
    "unity_scene_template",
    "unity_script_info",
    "unity_deep_serialize",
    "unity_window_management",
    "unity_input_system",
    "unity_time_settings",
    "unity_graphics_settings",
    "unity_environment_settings",
    "unity_audio_settings",
    "unity_component_copy",
    "unity_component_reset",
    "unity_scene_view",
    "unity_game_view",
    "unity_profiler_control",
    "unity_sync_solution",
    "unity_cloud_services",
    "unity_physics2d_config",
    "unity_search_query",
}

CLIENT_SIDE_TOOLS = {
    "unity_bridge_config",
    "unity_health_check",
    "unity_operation_status",
    "unity_submit_command",
    "unity_batch",
    "unity_help",
}

SPECIAL_HANDLER_TOOLS = {
    "unity_create_primitive",
    "unity_gameobject_set_active",
}


def _tool_names() -> set[str]:
    return {tool["name"] for tool in TOOL_DEFINITIONS}


class TestMCPToolNames:
    def test_all_expected_tools_defined(self) -> None:
        missing = EXPECTED_TOOL_NAMES - _tool_names()
        assert not missing, f"Missing MCP tool definitions: {missing}"

    def test_tool_count_is_exact(self) -> None:
        # The MCP surface is deprecated and frozen; pin the count exactly so an
        # accidental bulk drop (or addition) of tools is caught rather than
        # silently passing a loose floor. Update deliberately if the (frozen)
        # surface ever changes.
        assert len(_tool_names()) == 97

    def test_no_tool_name_changes(self) -> None:
        """Verify none of the original tool names have been renamed."""
        assert EXPECTED_TOOL_NAMES <= _tool_names()

    def test_current_surface_tools_defined(self) -> None:
        assert EXPECTED_CURRENT_SURFACE <= _tool_names()


class TestMCPToolMap:
    def test_tool_map_present(self) -> None:
        """The tool_map dict mapping tool names to bridge commands exists."""
        assert TOOL_COMMAND_MAP

    def test_known_mappings_intact(self) -> None:
        """Verify known tool->command mappings haven't changed."""
        for tool_name, cmd_type in EXPECTED_TOOL_MAP.items():
            assert TOOL_COMMAND_MAP.get(tool_name) == cmd_type

    def test_every_bridge_tool_is_mapped_or_explicitly_handled(self) -> None:
        mapped_or_handled = set(TOOL_COMMAND_MAP) | CLIENT_SIDE_TOOLS | SPECIAL_HANDLER_TOOLS
        assert _tool_names() - mapped_or_handled == set()


class TestMCPToolSchemas:
    def test_tools_have_descriptions(self) -> None:
        """Each tool definition should include a description."""
        for tool in TOOL_DEFINITIONS:
            assert tool["description"]

    def test_tools_have_input_schemas(self) -> None:
        """Each tool should define its inputSchema."""
        for tool in TOOL_DEFINITIONS:
            assert tool["inputSchema"]["type"] == "object"

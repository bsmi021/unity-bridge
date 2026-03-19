"""MCP tool definitions and dispatch for Unity Bridge.

Each entry in ``TOOL_DEFINITIONS`` mirrors the exact schema from the
legacy ``unity_bridge_mcp_server.py`` so that existing MCP clients
continue to work without changes.

Schemas live in ``schemas.py`` to keep both files under the 500 LOC limit.
"""

from __future__ import annotations

from typing import Any

from unity_bridge.mcp import schemas

# ---------------------------------------------------------------------------
# Tool name -> bridge command type mapping
# ---------------------------------------------------------------------------

TOOL_COMMAND_MAP: dict[str, str] = {
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

# ---------------------------------------------------------------------------
# Full tool definitions list
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "unity_run_tests",
        "description": (
            "Execute Unity tests (EditMode or PlayMode). "
            "10x-30x faster than batch mode when Unity is open."
        ),
        "inputSchema": schemas.run_tests(),
    },
    {
        "name": "unity_query_hierarchy",
        "description": "Inspect GameObject hierarchy in the active Unity scene.",
        "inputSchema": schemas.query_hierarchy(),
    },
    {
        "name": "unity_get_component_data",
        "description": "Read component field values from a GameObject.",
        "inputSchema": schemas.get_component_data(),
    },
    {
        "name": "unity_set_component_data",
        "description": "Modify component field values on a GameObject.",
        "inputSchema": schemas.set_component_data(),
    },
    {
        "name": "unity_add_component",
        "description": "Add a component to a GameObject dynamically.",
        "inputSchema": schemas.add_component(),
    },
    {
        "name": "unity_validate_prefab",
        "description": "Check prefab integrity and references.",
        "inputSchema": schemas.validate_prefab(),
    },
    {
        "name": "unity_scene_operation",
        "description": "Load, create, or save Unity scenes.",
        "inputSchema": schemas.scene_operation(),
    },
    {
        "name": "unity_prefab_operation",
        "description": "Instantiate or manage prefabs in the scene.",
        "inputSchema": schemas.prefab_operation(),
    },
    {
        "name": "unity_playmode_control",
        "description": "Control Unity Editor play mode (play, pause, stop).",
        "inputSchema": schemas.playmode_control(),
    },
    {
        "name": "unity_read_console",
        "description": "Read Unity console logs. Supports stack trace truncation.",
        "inputSchema": schemas.read_console(),
    },
    {
        "name": "unity_capture_screenshot",
        "description": "Capture Unity game view screenshot.",
        "inputSchema": schemas.capture_screenshot(),
    },
    {
        "name": "unity_profiler_sample",
        "description": "Capture Unity profiler performance metrics snapshot.",
        "inputSchema": schemas.profiler_sample(),
    },
    {
        "name": "unity_material_operation",
        "description": "Modify material properties programmatically.",
        "inputSchema": schemas.material_operation(),
    },
    {
        "name": "unity_asset_operation",
        "description": "Find and query Unity assets in the project.",
        "inputSchema": schemas.asset_operation(),
    },
    {
        "name": "unity_build_operation",
        "description": "Trigger Unity builds for various platforms.",
        "inputSchema": schemas.build_operation(),
    },
    {
        "name": "unity_animator_operation",
        "description": "Control Unity Animator states, parameters, and transitions.",
        "inputSchema": schemas.animator_operation(),
    },
    {
        "name": "unity_bridge_config",
        "description": "Configure Unity Bridge MCP server settings.",
        "inputSchema": schemas.bridge_config(),
    },
    {
        "name": "unity_clear_console",
        "description": "Clear all Unity console logs.",
        "inputSchema": schemas.clear_console(),
    },
    {
        "name": "unity_get_selection",
        "description": "Get currently selected GameObjects in Unity Editor.",
        "inputSchema": schemas.get_selection(),
    },
    {
        "name": "unity_refresh_assets",
        "description": "Refresh Unity asset database.",
        "inputSchema": schemas.refresh_assets(),
    },
    {
        "name": "unity_focus_object",
        "description": "Focus Unity scene view camera on a specific GameObject.",
        "inputSchema": schemas.focus_object(),
    },
    {
        "name": "unity_health_check",
        "description": "Check Unity Bridge health status and diagnostics.",
        "inputSchema": schemas.health_check(),
    },
    {
        "name": "unity_compile",
        "description": "Trigger script compilation and wait for completion.",
        "inputSchema": schemas.compile_scripts(),
    },
    {
        "name": "unity_execute_menu_item",
        "description": "Execute any Unity menu command by path.",
        "inputSchema": schemas.execute_menu_item(),
    },
    {
        "name": "unity_batch",
        "description": "Execute multiple Unity commands in a single round-trip.",
        "inputSchema": schemas.batch(),
    },
    {
        "name": "unity_help",
        "description": "Get help on Unity Bridge commands and workflows.",
        "inputSchema": schemas.help_topic(),
    },
]

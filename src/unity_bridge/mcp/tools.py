"""MCP tool definitions and dispatch for Unity Bridge.

Each entry in ``TOOL_DEFINITIONS`` mirrors the exact schema from the
legacy ``unity_bridge_mcp_server.py`` so that existing MCP clients
continue to work without changes.

Schemas live in ``schemas.py`` to keep both files under the 500 LOC limit.
"""

from __future__ import annotations

from typing import Any

from unity_bridge.mcp import (
    schemas,
    schemas_ext,
    schemas_phase3,
    schemas_phase4,
    schemas_phase5,
    schemas_pipeline,
)

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
    "unity_player_settings": "player-settings-operation",
    "unity_asset_extended": "asset-extended-operation",
    "unity_build_profile": "build-profile-operation",
    "unity_package_operation": "package-operation",
    "unity_compilation_pipeline": "compilation-pipeline",
    "unity_undo_operation": "undo-operation",
    "unity_prefab_overrides": "prefab-override",
    "unity_list_tests": "list-tests",
    "unity_gameobject_utility": "gameobject-utility",
    "unity_lightmap_operation": "lightmap-operation",
    "unity_shader_inspection": "shader-inspection",
    "unity_scene_extended": "scene-setup-operation",
    "unity_import_settings": "import-settings-operation",
    "unity_set_selection": "set-selection",
    "unity_editor_prefs": "editor-prefs",
    "unity_build_scenes": "build-scenes",
    "unity_transform": "transform-operation",
    "unity_serialized_property": "serialized-property",
    "unity_physics_config": "physics-config",
    "unity_quality_settings": "quality-settings",
    "unity_tags_layers": "tags-layers",
    "unity_editor_config": "editor-config",
    # Phase 5: Quick Wins
    "unity_remove_component": "remove-component",
    "unity_component_toggle": "component-toggle",
    "unity_console_log": "console-log",
    # Phase 4 expansion: Build, Platform, Pipeline
    "unity_script_execution_order": "script-execution-order",
    "unity_assembly_reload_lock": "assembly-reload-lock",
    "unity_find_references": "find-references",
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
        "inputSchema": schemas_ext.batch(),
    },
    {
        "name": "unity_help",
        "description": "Get help on Unity Bridge commands and workflows.",
        "inputSchema": schemas_ext.help_topic(),
    },
    {
        "name": "unity_player_settings",
        "description": "Read/write Unity PlayerSettings and manage scripting define symbols.",
        "inputSchema": schemas_ext.player_settings(),
    },
    {
        "name": "unity_asset_extended",
        "description": "Extended asset operations: create, delete, copy, move, deps, guid, folder management, export/import.",
        "inputSchema": schemas_ext.asset_extended(),
    },
    {
        "name": "unity_build_profile",
        "description": "Manage Unity 6 Build Profiles: list, get/set active, inspect details.",
        "inputSchema": schemas_ext.build_profile(),
    },
    {
        "name": "unity_package_operation",
        "description": "Unity Package Manager: list, search, add, remove, info, embed, resolve packages.",
        "inputSchema": schemas_ext.package_operation(),
    },
    {
        "name": "unity_compilation_pipeline",
        "description": "Query project assemblies, scripting defines, and code optimization.",
        "inputSchema": schemas_ext.compilation_pipeline(),
    },
    {
        "name": "unity_undo_operation",
        "description": "Manage Unity Editor undo/redo history.",
        "inputSchema": schemas_ext.undo_operation(),
    },
    {
        "name": "unity_prefab_overrides",
        "description": "List, apply, or revert prefab instance overrides.",
        "inputSchema": schemas_ext.prefab_overrides(),
    },
    {
        "name": "unity_list_tests",
        "description": "Discover available tests without running them.",
        "inputSchema": schemas_ext.list_tests(),
    },
    {
        "name": "unity_gameobject_utility",
        "description": "Find missing scripts, manage static flags, layers, and tags.",
        "inputSchema": schemas_ext.gameobject_utility(),
    },
    {
        "name": "unity_lightmap_operation",
        "description": "Lightmap baking: bake, cancel, clear, check status, read settings.",
        "inputSchema": schemas_phase3.unity_lightmap_operation(),
    },
    {
        "name": "unity_shader_inspection",
        "description": (
            "Inspect Unity shaders: list all, get info, check errors, "
            "enumerate properties, find by property, list keywords."
        ),
        "inputSchema": schemas_phase3.shader_inspection(),
    },
    {
        "name": "unity_scene_extended",
        "description": (
            "Extended scene management: save/restore multi-scene setups, "
            "play mode start scene, cross-scene refs, preview scenes."
        ),
        "inputSchema": schemas_phase3.unity_scene_extended(),
    },
    {
        "name": "unity_import_settings",
        "description": (
            "Asset import settings: get, set, reimport, bulk-set, "
            "save/apply templates for textures, models, audio."
        ),
        "inputSchema": schemas_phase3.import_settings(),
    },
    {
        "name": "unity_set_selection",
        "description": "Set or clear the Unity Editor selection programmatically.",
        "inputSchema": schemas_phase4.set_selection(),
    },
    {
        "name": "unity_editor_prefs",
        "description": (
            "Read/write EditorPrefs and SessionState values (string, int, float, bool)."
        ),
        "inputSchema": schemas_phase4.editor_prefs(),
    },
    {
        "name": "unity_build_scenes",
        "description": (
            "Manage Build Settings scene list: list, add, remove, enable, disable, reorder scenes."
        ),
        "inputSchema": schemas_phase4.build_scenes(),
    },
    {
        "name": "unity_transform",
        "description": (
            "Dedicated transform control: get/set position, rotation, scale, "
            "reparent GameObjects, set sibling index. Supports Undo."
        ),
        "inputSchema": schemas_phase4.transform_operation(),
    },
    {
        "name": "unity_serialized_property",
        "description": (
            "Access ALL serialized fields including [SerializeField] private fields. "
            "List, get, or set any property via Unity's SerializedObject API."
        ),
        "inputSchema": schemas_phase4.serialized_property(),
    },
    {
        "name": "unity_physics_config",
        "description": (
            "Physics configuration: get/set gravity, solver settings, "
            "read/modify the 32x32 layer collision matrix."
        ),
        "inputSchema": schemas_phase4.physics_config(),
    },
    {
        "name": "unity_quality_settings",
        "description": (
            "Quality settings: list levels, get current settings "
            "(shadows, AA, LOD, vsync), switch active level."
        ),
        "inputSchema": schemas_phase4.quality_settings(),
    },
    {
        "name": "unity_tags_layers",
        "description": (
            "Tags and layers management: list/add tags, list/add layers, "
            "list/add sorting layers via TagManager."
        ),
        "inputSchema": schemas_phase4.tags_layers(),
    },
    {
        "name": "unity_editor_config",
        "description": (
            "Editor settings: enter play mode options, serialization mode, "
            "async shader compilation, line endings, root namespace."
        ),
        "inputSchema": schemas_phase4.editor_config(),
    },
    # Phase 5: Quick Wins
    {
        "name": "unity_create_primitive",
        "description": (
            "Create primitives (cube, sphere, etc.), lights, cameras, "
            "or particle systems in the scene."
        ),
        "inputSchema": schemas_phase5.create_primitive(),
    },
    {
        "name": "unity_remove_component",
        "description": "Remove a component from a GameObject (cannot remove Transform).",
        "inputSchema": schemas_phase5.remove_component(),
    },
    {
        "name": "unity_component_toggle",
        "description": (
            "Enable or disable a component (Behaviour, Renderer, or Collider subclasses)."
        ),
        "inputSchema": schemas_phase5.component_toggle(),
    },
    {
        "name": "unity_gameobject_set_active",
        "description": "Activate or deactivate a GameObject (SetActive).",
        "inputSchema": schemas_phase5.gameobject_set_active(),
    },
    {
        "name": "unity_console_log",
        "description": "Log a custom message to the Unity Console (log, warning, or error).",
        "inputSchema": schemas_phase5.console_log(),
    },
    # Phase 4 expansion: Build, Platform, Pipeline
    {
        "name": "unity_script_execution_order",
        "description": (
            "Get or set MonoScript execution order. "
            "List all scripts with their order, or set a specific script's order."
        ),
        "inputSchema": schemas_pipeline.script_execution_order(),
    },
    {
        "name": "unity_assembly_reload_lock",
        "description": (
            "Lock/unlock assembly reloading. "
            "Prevents domain reload during batch operations."
        ),
        "inputSchema": schemas_pipeline.assembly_reload_lock(),
    },
    {
        "name": "unity_find_references",
        "description": (
            "Find all references to an asset in loaded scenes. "
            "Searches SerializedProperty ObjectReferences across all components."
        ),
        "inputSchema": schemas_pipeline.find_references(),
    },
]

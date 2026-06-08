"""Extended MCP tool definitions for Unity Bridge."""

from __future__ import annotations

from typing import Any

from unity_bridge.mcp import (
    schemas_authoring,
    schemas_core_packages,
    schemas_editor_state,
    schemas_multiplayer,
    schemas_phase4_ext,
    schemas_phase4_misc,
    schemas_phase6,
    schemas_rendering,
    schemas_unity64,
)


def get_tool_definitions() -> list[dict[str, Any]]:
    """Return tool definitions split out of tools.py."""
    return [
        {
            "name": "unity_navmesh",
            "description": (
                "NavMesh operations: bake, clear, get/set settings, list areas with costs."
            ),
            "inputSchema": schemas_phase4_ext.navmesh_operation(),
        },
        {
            "name": "unity_animation_clip",
            "description": (
                "Animation clip operations: create, get-info, set-curve, "
                "get-curves, add-event, set-properties."
            ),
            "inputSchema": schemas_phase4_ext.animation_clip(),
        },
        {
            "name": "unity_terrain",
            "description": (
                "Terrain operations: create, get-info, set/get heightmap "
                "regions, modify terrain settings."
            ),
            "inputSchema": schemas_phase4_ext.terrain_operation(),
        },
        {
            "name": "unity_reflection_probe",
            "description": (
                "Reflection probe operations: bake single or all probes, "
                "list probes, get probe info."
            ),
            "inputSchema": schemas_phase4_ext.reflection_probe(),
        },
        {
            "name": "unity_occlusion_culling",
            "description": (
                "Occlusion culling: compute, clear, "
                "get settings (smallestOccluder, smallestHole, backfaceThreshold)."
            ),
            "inputSchema": schemas_phase4_ext.occlusion_culling(),
        },
        {
            "name": "unity_addressables",
            "description": (
                "Addressables: list groups, build content, clean cache, "
                "mark asset addressable, set address key."
            ),
            "inputSchema": schemas_phase4_ext.addressables_operation(),
        },
        {
            "name": "unity_tilemap",
            "description": (
                "2D Tilemap: set/get tiles, fill box, clear all tiles, "
                "get bounds, compress bounds."
            ),
            "inputSchema": schemas_phase4_ext.tilemap_operation(),
        },
        {
            "name": "unity_clipboard",
            "description": "Read or write the Unity Editor system clipboard.",
            "inputSchema": schemas_phase4_misc.clipboard(),
        },
        {
            "name": "unity_preset",
            "description": "Create, apply, validate, or list Unity Preset assets.",
            "inputSchema": schemas_phase4_misc.preset_operation(),
        },
        {
            "name": "unity_scene_template",
            "description": "List, create, or instantiate Unity Scene Template assets.",
            "inputSchema": schemas_phase4_misc.scene_template(),
        },
        {
            "name": "unity_script_info",
            "description": "Inspect MonoScript assets and find component source scripts.",
            "inputSchema": schemas_phase4_misc.script_info(),
        },
        {
            "name": "unity_deep_serialize",
            "description": "Read or write full EditorJsonUtility component serialization.",
            "inputSchema": schemas_phase4_misc.deep_serialize(),
        },
        {
            "name": "unity_window_management",
            "description": "List, open, focus, or close Unity Editor windows.",
            "inputSchema": schemas_phase4_misc.window_management(),
        },
        {
            "name": "unity_input_system",
            "description": "List, export, or import Input System action assets.",
            "inputSchema": schemas_phase4_misc.input_system(),
        },
        {
            "name": "unity_ui_toolkit",
            "description": "Inspect and author UI Toolkit UXML, USS, PanelSettings, and UIDocument.",
            "inputSchema": schemas_authoring.ui_toolkit(),
        },
        {
            "name": "unity_render_pipeline",
            "description": "Inspect and assign Unity render pipeline assets and quality overrides.",
            "inputSchema": schemas_rendering.render_pipeline(),
        },
        {
            "name": "unity_graphics_state",
            "description": "Trace, inspect, and warm up GraphicsStateCollection files.",
            "inputSchema": schemas_rendering.graphics_state(),
        },
        {
            "name": "unity_graph_toolkit",
            "description": "Inspect and export Unity Graph Toolkit graph assets.",
            "inputSchema": schemas_editor_state.graph_toolkit(),
        },
        {
            "name": "unity_scene_state",
            "description": "Read and set deterministic Scene View/editor state.",
            "inputSchema": schemas_editor_state.scene_state(),
        },
        {
            "name": "unity_entities",
            "description": "Inspect Unity Entities package worlds, systems, and runtime state.",
            "inputSchema": schemas_core_packages.entities(),
        },
        {
            "name": "unity_adaptive_performance",
            "description": "Inspect Adaptive Performance settings and scaler profiles.",
            "inputSchema": schemas_core_packages.adaptive_performance(),
        },
        {
            "name": "unity_multiplayer_playmode",
            "description": "Inspect read-only Multiplayer Play Mode API and package state.",
            "inputSchema": schemas_multiplayer.multiplayer_playmode(),
        },
        {
            "name": "unity_time_settings",
            "description": "Read or update Unity Time settings.",
            "inputSchema": schemas_phase6.time_settings(),
        },
        {
            "name": "unity_graphics_settings",
            "description": "Read or update Unity Graphics settings.",
            "inputSchema": schemas_phase6.graphics_settings(),
        },
        {
            "name": "unity_environment_settings",
            "description": "Read or update Unity scene environment settings.",
            "inputSchema": schemas_phase6.environment_settings(),
        },
        {
            "name": "unity_audio_settings",
            "description": "Read or update Unity audio settings.",
            "inputSchema": schemas_phase6.audio_settings(),
        },
        {
            "name": "unity_object_identity",
            "description": (
                "Resolve Unity object identity across EntityId, GlobalObjectId, "
                "legacy instance ID, scene path, and asset path."
            ),
            "inputSchema": schemas_unity64.object_identity(),
        },
        {
            "name": "unity_project_auditor",
            "description": (
                "Check availability, run, or summarize Unity Project Auditor reports."
            ),
            "inputSchema": schemas_unity64.project_auditor(),
        },
    ]


TOOL_COMMAND_MAP_EXT: dict[str, str] = {
    "unity_navmesh": "navmesh-operation",
    "unity_animation_clip": "animation-clip",
    "unity_terrain": "terrain-operation",
    "unity_reflection_probe": "reflection-probe",
    "unity_occlusion_culling": "occlusion-culling",
    "unity_addressables": "addressables",
    "unity_tilemap": "tilemap-operation",
    "unity_clipboard": "clipboard",
    "unity_preset": "preset-operation",
    "unity_scene_template": "scene-template",
    "unity_script_info": "script-info",
    "unity_deep_serialize": "deep-serialize",
    "unity_window_management": "window-management",
    "unity_input_system": "input-system",
    "unity_ui_toolkit": "ui-toolkit",
    "unity_render_pipeline": "render-pipeline",
    "unity_graphics_state": "graphics-state",
    "unity_graph_toolkit": "graph-toolkit",
    "unity_scene_state": "scene-state",
    "unity_entities": "entities",
    "unity_adaptive_performance": "adaptive-performance",
    "unity_multiplayer_playmode": "multiplayer-playmode",
    "unity_time_settings": "time-settings",
    "unity_graphics_settings": "graphics-settings",
    "unity_environment_settings": "environment-settings",
    "unity_audio_settings": "audio-settings",
    "unity_object_identity": "object-identity",
    "unity_project_auditor": "project-auditor",
}

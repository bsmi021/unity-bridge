"""Extended MCP tool definitions for Unity Bridge (Phase 4 expansion and beyond).

Split from tools.py to stay under the 500 LOC limit.
These definitions are appended to TOOL_DEFINITIONS in tools.py.
"""

from __future__ import annotations

from typing import Any

from unity_bridge.mcp import schemas_phase4_ext


def get_tool_definitions() -> list[dict[str, Any]]:
    """Return tool definitions for Phase 4 expansion: Specialized Workflow Gaps."""
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
    ]


# Tool name -> command type mappings for this group
TOOL_COMMAND_MAP_EXT: dict[str, str] = {
    "unity_navmesh": "navmesh-operation",
    "unity_animation_clip": "animation-clip",
    "unity_terrain": "terrain-operation",
    "unity_reflection_probe": "reflection-probe",
    "unity_occlusion_culling": "occlusion-culling",
    "unity_addressables": "addressables",
    "unity_tilemap": "tilemap-operation",
}

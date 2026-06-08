"""MCP tool input schemas for Unity Bridge (Phase 4 expansion: Specialized Workflows).

Schemas: navmesh, animation-clip, terrain, reflection-probe,
occlusion-culling, addressables, tilemap.
Split from schemas_phase4.py to stay under 500 LOC.
"""

from __future__ import annotations

from typing import Any


def navmesh_operation() -> dict[str, Any]:
    """Consolidated NavMesh operation tool."""
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["bake", "clear", "get-settings", "set-settings", "get-areas"],
                "description": "NavMesh operation to perform",
            },
            "agentRadius": {
                "type": "number",
                "description": "Agent radius (for 'set-settings')",
            },
            "agentHeight": {
                "type": "number",
                "description": "Agent height (for 'set-settings')",
            },
            "agentSlope": {
                "type": "number",
                "description": "Max slope angle in degrees (for 'set-settings')",
            },
            "agentClimb": {
                "type": "number",
                "description": "Max step height (for 'set-settings')",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds",
                "default": 60,
            },
        },
        "required": ["operation"],
    }


def animation_clip() -> dict[str, Any]:
    """Consolidated animation clip tool."""
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": [
                    "create",
                    "get-info",
                    "set-curve",
                    "get-curves",
                    "add-event",
                    "set-properties",
                ],
                "description": "Animation clip operation to perform",
            },
            "clipPath": {
                "type": "string",
                "description": (
                    "Asset path to the AnimationClip (e.g. 'Assets/Anim/Walk.anim'). "
                    "Required for all operations."
                ),
            },
            "propertyName": {
                "type": "string",
                "description": "Property name to animate (for 'set-curve')",
            },
            "relativePath": {
                "type": "string",
                "description": "Relative path to target object (for 'set-curve')",
                "default": "",
            },
            "componentType": {
                "type": "string",
                "description": "Component type (for 'set-curve')",
                "default": "Transform",
            },
            "keyframes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "time": {"type": "number"},
                        "value": {"type": "number"},
                    },
                    "required": ["time", "value"],
                },
                "description": "Keyframe data (for 'set-curve')",
            },
            "eventTime": {
                "type": "number",
                "description": "Event time in seconds (for 'add-event')",
            },
            "eventFunction": {
                "type": "string",
                "description": "Function name for event (for 'add-event')",
                "default": "OnAnimationEvent",
            },
            "eventStringParam": {
                "type": "string",
                "description": "String parameter for event (for 'add-event')",
            },
            "eventIntParam": {
                "type": "integer",
                "description": "Int parameter for event (for 'add-event')",
            },
            "eventFloatParam": {
                "type": "number",
                "description": "Float parameter for event (for 'add-event')",
            },
            "looping": {
                "type": "boolean",
                "description": "Set loop mode (for 'set-properties')",
            },
            "setLooping": {
                "type": "boolean",
                "description": "Flag to indicate looping should be set",
            },
            "wrapMode": {
                "type": "string",
                "description": "Wrap mode (for 'set-properties')",
                "enum": [
                    "Default",
                    "Once",
                    "Loop",
                    "PingPong",
                    "ClampForever",
                ],
            },
            "frameRate": {
                "type": "number",
                "description": "Frame rate (for 'create' or 'set-properties')",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds",
                "default": 15,
            },
        },
        "required": ["operation", "clipPath"],
    }


def terrain_operation() -> dict[str, Any]:
    """Consolidated terrain operation tool."""
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": [
                    "create",
                    "get-info",
                    "set-heights",
                    "get-heights",
                    "set-settings",
                ],
                "description": "Terrain operation to perform",
            },
            "terrainName": {
                "type": "string",
                "description": "Terrain GameObject name (optional, uses active terrain)",
            },
            "terrainDataPath": {
                "type": "string",
                "description": "Asset path for TerrainData (for 'create')",
            },
            "heightmapResolution": {
                "type": "integer",
                "description": "Heightmap resolution (for 'create' or 'set-settings')",
            },
            "sizeX": {
                "type": "number",
                "description": "Terrain width (for 'create' or 'set-settings')",
            },
            "sizeY": {
                "type": "number",
                "description": "Terrain height (for 'create' or 'set-settings')",
            },
            "sizeZ": {
                "type": "number",
                "description": "Terrain depth (for 'create' or 'set-settings')",
            },
            "heightX": {
                "type": "integer",
                "description": "Start X for height operations",
                "default": 0,
            },
            "heightY": {
                "type": "integer",
                "description": "Start Y for height operations",
                "default": 0,
            },
            "heightWidth": {
                "type": "integer",
                "description": "Width for 'get-heights'",
                "default": 16,
            },
            "heightHeight": {
                "type": "integer",
                "description": "Height for 'get-heights'",
                "default": 16,
            },
            "heights": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "values": {
                            "type": "array",
                            "items": {"type": "number"},
                        },
                    },
                },
                "description": "2D height data rows (for 'set-heights')",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds",
                "default": 30,
            },
        },
        "required": ["operation"],
    }


def reflection_probe() -> dict[str, Any]:
    """Consolidated reflection probe tool."""
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["bake", "bake-all", "list", "get-info"],
                "description": "Reflection probe operation to perform",
            },
            "gameObjectPath": {
                "type": "string",
                "description": ("Hierarchy path to the probe. Required for: bake, get-info."),
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds",
                "default": 30,
            },
        },
        "required": ["operation"],
    }


def occlusion_culling() -> dict[str, Any]:
    """Consolidated occlusion culling tool."""
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["bake", "clear", "get-settings"],
                "description": "Occlusion culling operation to perform",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds",
                "default": 120,
            },
        },
        "required": ["operation"],
    }


def addressables_operation() -> dict[str, Any]:
    """Consolidated Addressables tool."""
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": [
                    "list-groups",
                    "build",
                    "clean-cache",
                    "mark-addressable",
                    "set-address",
                    "list-profiles",
                    "set-active-profile",
                    "list-labels",
                    "set-label",
                    "list-schemas",
                    "analyze",
                ],
                "description": "Addressables operation to perform",
            },
            "assetPath": {
                "type": "string",
                "description": ("Asset path. Required for: mark-addressable, set-address."),
            },
            "address": {
                "type": "string",
                "description": "Address key (for 'set-address')",
            },
            "profileId": {"type": "string", "description": "Addressables profile ID"},
            "profileName": {"type": "string", "description": "Addressables profile name"},
            "label": {"type": "string", "description": "Addressables label"},
            "enable": {"type": "boolean", "description": "Enable or disable label"},
            "force": {"type": "boolean", "description": "Create label if missing"},
            "analyzeRule": {"type": "string", "description": "Analyze rule name"},
            "outputPath": {"type": "string", "description": "Optional output path"},
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds",
                "default": 60,
            },
        },
        "required": ["operation"],
    }


def tilemap_operation() -> dict[str, Any]:
    """Consolidated 2D tilemap tool."""
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": [
                    "set-tile",
                    "get-tile",
                    "fill-box",
                    "clear",
                    "get-bounds",
                    "compress-bounds",
                ],
                "description": "Tilemap operation to perform",
            },
            "tilemapPath": {
                "type": "string",
                "description": "Hierarchy path to the Tilemap component",
            },
            "tilePath": {
                "type": "string",
                "description": (
                    "Asset path to a TileBase asset. Required for: set-tile, fill-box."
                ),
            },
            "posX": {
                "type": "integer",
                "description": "Cell X position",
                "default": 0,
            },
            "posY": {
                "type": "integer",
                "description": "Cell Y position",
                "default": 0,
            },
            "posZ": {
                "type": "integer",
                "description": "Cell Z position",
                "default": 0,
            },
            "startX": {
                "type": "integer",
                "description": "Fill start X (for 'fill-box')",
            },
            "startY": {
                "type": "integer",
                "description": "Fill start Y (for 'fill-box')",
            },
            "endX": {
                "type": "integer",
                "description": "Fill end X (for 'fill-box')",
            },
            "endY": {
                "type": "integer",
                "description": "Fill end Y (for 'fill-box')",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds",
                "default": 15,
            },
        },
        "required": ["operation"],
    }

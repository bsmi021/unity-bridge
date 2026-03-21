"""MCP tool input schemas for Unity Bridge (part 4: Phase 4 critical gaps).

Phase 4 schemas: set-selection, editor-prefs, build-scenes, transform,
serialized-property, physics-config, quality-settings, tags-layers, editor-config.
Split from schemas_ext.py to stay under 500 LOC.
"""

from __future__ import annotations

from typing import Any


def set_selection() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["set", "clear"],
                "description": "Selection operation to perform",
            },
            "gameObjectPaths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Hierarchy paths to select (required for 'set')",
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["operation"],
    }


def editor_prefs() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["get", "set", "delete", "has"],
                "description": "EditorPrefs operation to perform",
            },
            "key": {
                "type": "string",
                "description": "Preference key",
            },
            "value": {
                "type": "string",
                "description": "Value to set (as string; interpreted per valueType)",
            },
            "valueType": {
                "type": "string",
                "enum": ["string", "int", "float", "bool"],
                "description": "Type of the value",
                "default": "string",
            },
            "scope": {
                "type": "string",
                "enum": ["prefs", "session"],
                "description": "Storage scope: EditorPrefs or SessionState",
                "default": "prefs",
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["operation"],
    }


def build_scenes() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["list", "add", "remove", "enable", "disable", "reorder"],
                "description": "Build scenes operation to perform",
            },
            "scenePath": {
                "type": "string",
                "description": "Scene asset path (e.g. 'Assets/Scenes/Main.unity')",
            },
            "index": {
                "type": "integer",
                "description": "Position to insert at (for 'add') or reorder to (for 'reorder')",
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["operation"],
    }


def transform_operation() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["get", "set", "parent", "sibling-index"],
                "description": "Transform operation to perform",
            },
            "gameObjectPath": {
                "type": "string",
                "description": "Hierarchy path to the GameObject",
            },
            "position": {
                "type": "object",
                "properties": {
                    "x": {"type": "number"},
                    "y": {"type": "number"},
                    "z": {"type": "number"},
                    "isSet": {"type": "boolean", "default": True},
                },
                "description": "World position (for 'set')",
            },
            "localPosition": {
                "type": "object",
                "properties": {
                    "x": {"type": "number"},
                    "y": {"type": "number"},
                    "z": {"type": "number"},
                    "isSet": {"type": "boolean", "default": True},
                },
                "description": "Local position (for 'set' with useLocal)",
            },
            "rotation": {
                "type": "object",
                "properties": {
                    "x": {"type": "number"},
                    "y": {"type": "number"},
                    "z": {"type": "number"},
                    "isSet": {"type": "boolean", "default": True},
                },
                "description": "Euler rotation (for 'set')",
            },
            "scale": {
                "type": "object",
                "properties": {
                    "x": {"type": "number"},
                    "y": {"type": "number"},
                    "z": {"type": "number"},
                    "isSet": {"type": "boolean", "default": True},
                },
                "description": "Local scale (for 'set')",
            },
            "useLocal": {
                "type": "boolean",
                "description": "Use local coordinates for rotation",
                "default": False,
            },
            "parentPath": {
                "type": "string",
                "description": "Hierarchy path of new parent (for 'parent'). Omit to unparent.",
            },
            "worldPositionStays": {
                "type": "boolean",
                "description": "Preserve world position during reparent",
                "default": True,
            },
            "siblingIndex": {
                "type": "integer",
                "description": "Target sibling index (for 'sibling-index')",
            },
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds",
                "default": 10,
            },
        },
        "required": ["operation", "gameObjectPath"],
    }


def serialized_property() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["list", "get", "set"],
                "description": "Property operation to perform",
            },
            "gameObjectPath": {
                "type": "string",
                "description": "Hierarchy path to the GameObject",
            },
            "componentType": {
                "type": "string",
                "description": "Component type name (e.g. 'Transform', 'MyScript')",
            },
            "propertyPath": {
                "type": "string",
                "description": "SerializedProperty path. Required for: get, set.",
            },
            "valueJson": {
                "type": "string",
                "description": "JSON value to set. Required for: set.",
            },
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds",
                "default": 15,
            },
        },
        "required": ["operation", "gameObjectPath", "componentType"],
    }


def physics_config() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["get", "set", "collision-matrix-get", "collision-matrix-set"],
                "description": "Physics operation to perform",
            },
            "gravity": {
                "type": "object",
                "properties": {
                    "x": {"type": "number"},
                    "y": {"type": "number"},
                    "z": {"type": "number"},
                    "isSet": {"type": "boolean", "default": True},
                },
                "description": "World gravity vector (for 'set')",
            },
            "defaultSolverIterations": {
                "type": "integer",
                "description": "Default solver iteration count (for 'set')",
            },
            "bounceThreshold": {
                "type": "number",
                "description": "Bounce threshold velocity (for 'set')",
            },
            "sleepThreshold": {
                "type": "number",
                "description": "Sleep threshold energy (for 'set')",
            },
            "defaultContactOffset": {
                "type": "number",
                "description": "Default contact offset (for 'set')",
            },
            "layer1": {
                "type": "integer",
                "description": "First layer index 0-31 (for 'collision-matrix-set')",
            },
            "layer2": {
                "type": "integer",
                "description": "Second layer index 0-31 (for 'collision-matrix-set')",
            },
            "ignoreCollision": {
                "type": "boolean",
                "description": "Ignore collision between layers",
                "default": False,
            },
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds",
                "default": 10,
            },
        },
        "required": ["operation"],
    }


def quality_settings() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["list", "get", "set-level"],
                "description": "Quality settings operation to perform",
            },
            "level": {
                "type": "integer",
                "description": "Quality level index (for 'set-level')",
            },
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds",
                "default": 10,
            },
        },
        "required": ["operation"],
    }


def tags_layers() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": [
                    "list-tags",
                    "add-tag",
                    "list-layers",
                    "add-layer",
                    "list-sorting-layers",
                    "add-sorting-layer",
                ],
                "description": "Tags/layers operation to perform",
            },
            "tagName": {
                "type": "string",
                "description": "Tag name (for 'add-tag')",
            },
            "layerName": {
                "type": "string",
                "description": "Layer name (for 'add-layer')",
            },
            "layerIndex": {
                "type": "integer",
                "description": "Specific layer slot 8-31 (for 'add-layer')",
            },
            "sortingLayerName": {
                "type": "string",
                "description": "Sorting layer name (for 'add-sorting-layer')",
            },
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds",
                "default": 15,
            },
        },
        "required": ["operation"],
    }


def editor_config() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["get", "set"],
                "description": "Editor config operation to perform",
            },
            "key": {
                "type": "string",
                "description": (
                    "Setting key for 'set'. Supported: "
                    "enterPlayModeOptionsEnabled, enterPlayModeOptions, "
                    "serializationMode, asyncShaderCompilation, "
                    "lineEndingsForNewScripts, projectGenerationRootNamespace"
                ),
            },
            "value": {
                "type": "string",
                "description": "New value for 'set' operation",
            },
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds",
                "default": 10,
            },
        },
        "required": ["operation"],
    }

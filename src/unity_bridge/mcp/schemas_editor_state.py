"""MCP schemas for Graph Toolkit and deterministic editor state."""

from __future__ import annotations

from typing import Any


def graph_toolkit() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["availability", "list-assets", "inspect", "export"],
            },
            "assetPath": {"type": "string", "description": "Graph asset path"},
            "includePorts": {"type": "boolean", "default": False},
            "includeVariables": {"type": "boolean", "default": False},
            "includeAnnotations": {"type": "boolean", "default": False},
            "maxElements": {"type": "integer", "minimum": 1},
            "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30},
        },
        "required": ["operation"],
    }


def _vec3_schema(description: str) -> dict[str, Any]:
    return {
        "type": "array",
        "items": {"type": "number"},
        "minItems": 3,
        "maxItems": 3,
        "description": description,
    }


def scene_state() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {"type": "string", "enum": ["get", "set", "reset-snap", "list-overlays"]},
            "showGrid": {"type": "boolean"},
            "gridSnapEnabled": {"type": "boolean"},
            "snapEnabled": {"type": "boolean"},
            "angleSnapEnabled": {"type": "boolean"},
            "scaleSnapEnabled": {"type": "boolean"},
            "gridSize": _vec3_schema("Scene View grid size"),
            "gridPosition": _vec3_schema("Scene View grid position"),
            "moveSnap": _vec3_schema("Move snap increments"),
            "rotateSnap": {"type": "number"},
            "scaleSnap": {"type": "number"},
            "drawGizmos": {"type": "boolean"},
            "use3dGizmos": {"type": "boolean"},
            "showSelectionOutline": {"type": "boolean"},
            "showSelectionWire": {"type": "boolean"},
            "activeTool": {"type": "string"},
            "pivotMode": {"type": "string"},
            "pivotRotation": {"type": "string"},
            "toolsHidden": {"type": "boolean"},
            "visibleLayers": {"type": "integer"},
            "lockedLayers": {"type": "integer"},
            "overlaysEnabled": {"type": "boolean"},
            "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 10},
        },
        "required": ["operation"],
    }

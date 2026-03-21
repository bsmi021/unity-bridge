"""MCP tool input schemas for Unity Bridge (part 6b: Inspector/Scene/Component gaps).

Phase 6b schemas: component-copy, component-reset, scene-view, game-view,
profiler-control.
"""

from __future__ import annotations

from typing import Any


def component_copy() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["copy", "paste"],
                "description": "Component copy operation to perform",
            },
            "gameObjectPath": {
                "type": "string",
                "description": "Hierarchy path to the GameObject",
            },
            "componentType": {
                "type": "string",
                "description": "Component type name (e.g. 'BoxCollider')",
            },
            "dataJson": {
                "type": "string",
                "description": ("JSON data for paste (optional; uses copy buffer if omitted)"),
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["operation", "gameObjectPath", "componentType"],
    }


def component_reset() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "gameObjectPath": {
                "type": "string",
                "description": "Hierarchy path to the GameObject",
            },
            "componentType": {
                "type": "string",
                "description": "Component type name to reset to defaults",
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["gameObjectPath", "componentType"],
    }


def scene_view() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["get-camera", "set-camera", "toggle-2d", "set-draw-mode"],
                "description": "Scene View operation to perform",
            },
            "pivot": {
                "type": "object",
                "properties": {
                    "x": {"type": "number"},
                    "y": {"type": "number"},
                    "z": {"type": "number"},
                    "isSet": {"type": "boolean", "default": True},
                },
                "description": "Camera pivot point (for set-camera)",
            },
            "rotation": {
                "type": "object",
                "properties": {
                    "x": {"type": "number"},
                    "y": {"type": "number"},
                    "z": {"type": "number"},
                    "isSet": {"type": "boolean", "default": True},
                },
                "description": "Euler rotation (for set-camera)",
            },
            "size": {
                "type": "number",
                "description": "Camera orbit size (for set-camera)",
            },
            "orthographic": {
                "type": "boolean",
                "description": "Set orthographic projection (for set-camera)",
            },
            "setPerspective": {
                "type": "boolean",
                "description": "Set perspective projection (for set-camera)",
            },
            "enable2D": {
                "type": "boolean",
                "description": "Enable or disable 2D mode (for toggle-2d)",
            },
            "drawMode": {
                "type": "string",
                "description": (
                    "Draw mode: Textured, Wireframe, TexturedWire, "
                    "ShadedWireframe, Shaded (for set-draw-mode)"
                ),
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["operation"],
    }


def game_view() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["get", "set-resolution", "set-scale"],
                "description": "Game View operation to perform",
            },
            "width": {
                "type": "integer",
                "description": "Resolution width in pixels (for set-resolution)",
            },
            "height": {
                "type": "integer",
                "description": "Resolution height in pixels (for set-resolution)",
            },
            "scale": {
                "type": "number",
                "description": "Zoom scale, 1.0 = 100% (for set-scale)",
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["operation"],
    }


def profiler_control() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["start", "stop", "save", "memory"],
                "description": "Profiler control operation to perform",
            },
            "logFile": {
                "type": "string",
                "description": (
                    "Path for profiler data file (for start with logging, or save operation)"
                ),
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["operation"],
    }

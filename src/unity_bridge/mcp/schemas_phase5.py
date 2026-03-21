"""MCP tool input schemas for Unity Bridge (part 5: Phase 5 quick wins).

Phase 5 schemas: create-primitive, remove-component, component-toggle,
gameobject set-active, additive scene loading, console-log.
Split from schemas_phase4.py to stay under 500 LOC.
"""

from __future__ import annotations

from typing import Any


def create_primitive() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "primitiveType": {
                "type": "string",
                "enum": [
                    "cube",
                    "sphere",
                    "capsule",
                    "cylinder",
                    "plane",
                    "quad",
                    "directional-light",
                    "point-light",
                    "spot-light",
                    "area-light",
                    "camera",
                    "particle-system",
                ],
                "description": "Type of primitive or common object to create",
            },
            "gameObjectName": {
                "type": "string",
                "description": "Custom name for the created object (optional)",
            },
            "parentPath": {
                "type": "string",
                "description": "Hierarchy path of parent GameObject (optional)",
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["primitiveType"],
    }


def remove_component() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "gameObjectPath": {
                "type": "string",
                "description": "Hierarchy path to the GameObject",
            },
            "componentType": {
                "type": "string",
                "description": "Component type name to remove (cannot remove Transform)",
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["gameObjectPath", "componentType"],
    }


def component_toggle() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "gameObjectPath": {
                "type": "string",
                "description": "Hierarchy path to the GameObject",
            },
            "componentType": {
                "type": "string",
                "description": (
                    "Component type name. Must be a Behaviour, Renderer, "
                    "or Collider subclass to support enable/disable."
                ),
            },
            "enabled": {
                "type": "boolean",
                "description": "True to enable, false to disable",
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["gameObjectPath", "componentType", "enabled"],
    }


def gameobject_set_active() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "gameObjectPath": {
                "type": "string",
                "description": "Hierarchy path to the GameObject",
            },
            "active": {
                "type": "boolean",
                "description": "True to activate, false to deactivate",
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["gameObjectPath", "active"],
    }


def console_log() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Message text to log in the Unity Console",
            },
            "logType": {
                "type": "string",
                "enum": ["log", "warning", "error"],
                "description": "Log severity level",
                "default": "log",
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["message"],
    }

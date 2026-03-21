"""MCP tool input schemas for Phase 4 Misc: expanded capabilities.

Schemas: clipboard, preset, scene-template, script-info, deep-serialize,
window-management, input-system.
"""

from __future__ import annotations

from typing import Any


def clipboard() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["read", "write"],
                "description": "Clipboard operation to perform",
            },
            "text": {
                "type": "string",
                "description": "Text to write (required for 'write')",
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["operation"],
    }


def preset_operation() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["create", "apply", "can-apply", "list-defaults"],
                "description": "Preset operation to perform",
            },
            "sourcePath": {
                "type": "string",
                "description": "Asset path of source object (for 'create')",
            },
            "outputPath": {
                "type": "string",
                "description": "Where to save the preset (for 'create')",
            },
            "presetPath": {
                "type": "string",
                "description": "Preset asset path (for 'apply', 'can-apply')",
            },
            "targetPath": {
                "type": "string",
                "description": "Target asset path (for 'apply', 'can-apply')",
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["operation"],
    }


def scene_template() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["list", "create-from-scene", "instantiate"],
                "description": "Scene template operation to perform",
            },
            "scenePath": {
                "type": "string",
                "description": "Source scene path (for 'create-from-scene')",
            },
            "outputPath": {
                "type": "string",
                "description": "Output path (for 'create-from-scene', 'instantiate')",
            },
            "templatePath": {
                "type": "string",
                "description": "Template asset path (for 'instantiate')",
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["operation"],
    }


def script_info() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["info", "list", "find-component"],
                "description": "Script inspection operation to perform",
            },
            "assetPath": {
                "type": "string",
                "description": "Path to .cs script asset (for 'info')",
            },
            "gameObjectPath": {
                "type": "string",
                "description": "Hierarchy path (for 'find-component')",
            },
            "componentType": {
                "type": "string",
                "description": "Component type name (for 'find-component')",
            },
            "filter": {
                "type": "string",
                "description": "Filter scripts by name (for 'list')",
            },
            "maxResults": {
                "type": "integer",
                "description": "Max results for 'list' (default 500)",
                "default": 500,
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["operation"],
    }


def deep_serialize() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["get", "set"],
                "description": "Deep serialization operation",
            },
            "gameObjectPath": {
                "type": "string",
                "description": "Hierarchy path to the GameObject",
            },
            "componentType": {
                "type": "string",
                "description": "Component type name",
            },
            "json": {
                "type": "string",
                "description": "JSON data for 'set' operation",
            },
            "prettyPrint": {
                "type": "boolean",
                "description": "Format JSON output (default true)",
                "default": True,
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["operation", "gameObjectPath", "componentType"],
    }


def window_management() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["list", "open", "focus", "close"],
                "description": "Window management operation",
            },
            "windowName": {
                "type": "string",
                "description": (
                    "Window name: Scene, Game, Inspector, Console, Project, "
                    "Hierarchy, Animation, Animator, Profiler, PackageManager, Lighting"
                ),
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["operation"],
    }


def input_system() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["list-actions", "get-action-map", "export", "import"],
                "description": "Input System operation",
            },
            "assetPath": {
                "type": "string",
                "description": "Path to InputActionAsset",
            },
            "outputPath": {
                "type": "string",
                "description": "File path to save exported JSON",
            },
            "inputPath": {
                "type": "string",
                "description": "File path to read JSON from (for 'import')",
            },
            "json": {
                "type": "string",
                "description": "Inline JSON data (for 'import')",
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["operation"],
    }

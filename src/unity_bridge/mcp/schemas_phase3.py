"""MCP tool input schemas for Unity Bridge (part 3: Phase 3 specialized APIs).

Phase 3 schemas: shader-inspection, lightmap-operation, import-settings,
scene-extended. Split from schemas.py and schemas_ext.py to stay under 500 LOC.
"""

from __future__ import annotations

from typing import Any


def shader_inspection() -> dict[str, Any]:
    """Consolidated shader inspection tool with operation dispatch."""
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "description": "Shader operation to perform",
                "enum": [
                    "list",
                    "info",
                    "errors",
                    "properties",
                    "find-by-property",
                    "keywords",
                ],
            },
            "shaderName": {
                "type": "string",
                "description": (
                    "Full shader name (e.g. 'Universal Render Pipeline/Lit'). "
                    "Required for: info, errors, properties, keywords."
                ),
            },
            "propertyName": {
                "type": "string",
                "description": (
                    "Shader property name (e.g. '_MainTex'). Required for: find-by-property."
                ),
            },
            "errorsOnly": {
                "type": "boolean",
                "description": (
                    "Only return shaders with compilation errors (for 'list' operation)"
                ),
                "default": False,
            },
            "keywordFilter": {
                "type": "string",
                "description": (
                    "Optional filter: 'global', 'local', or omit for both "
                    "(for 'keywords' operation)"
                ),
                "enum": ["global", "local"],
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds",
                "default": 15,
            },
        },
        "required": ["operation"],
    }


def unity_scene_extended() -> dict[str, Any]:
    """Consolidated extended scene management tool with operation dispatch."""
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "description": "Scene operation to perform",
                "enum": [
                    "save",
                    "restore",
                    "list",
                    "play-start",
                    "cross-refs",
                    "list-loaded",
                    "preview-create",
                    "preview-close",
                ],
            },
            "setupName": {
                "type": "string",
                "description": (
                    "Setup name (alphanumeric, hyphens, underscores, max 64 chars). "
                    "Required for: setup-save, setup-restore."
                ),
            },
            "scenePath": {
                "type": "string",
                "description": (
                    "Scene path to set as play mode start scene (for 'play-start' operation)."
                ),
            },
            "clear": {
                "type": "boolean",
                "description": "Clear the play mode start scene (for 'play-start' operation)",
                "default": False,
            },
            "handle": {
                "type": "integer",
                "description": "Preview scene handle. Required for: preview-close.",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds",
                "default": 30,
            },
        },
        "required": ["operation"],
    }


def import_settings() -> dict[str, Any]:
    """Consolidated import settings tool with operation dispatch."""
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "description": "Import settings operation to perform",
                "enum": [
                    "get",
                    "set",
                    "reimport",
                    "bulk-set",
                    "template-save",
                    "template-apply",
                ],
            },
            "assetPath": {
                "type": "string",
                "description": (
                    "Asset path (e.g. 'Assets/Textures/Albedo.png'). "
                    "Required for: get, set, reimport, template-save, template-apply."
                ),
            },
            "settings": {
                "type": "object",
                "description": (
                    "Key-value pairs of settings to modify. Required for: set, bulk-set."
                ),
                "additionalProperties": True,
            },
            "force": {
                "type": "boolean",
                "description": ("Force reimport even if unchanged (for 'reimport' operation)"),
                "default": False,
            },
            "templateName": {
                "type": "string",
                "description": (
                    "Template name (alphanumeric, hyphens, underscores). "
                    "Required for: template-save, template-apply."
                ),
            },
            "folderPath": {
                "type": "string",
                "description": "Folder path for bulk operations. Required for: bulk-set.",
            },
            "filter": {
                "type": "string",
                "description": (
                    "Glob filter pattern for bulk operations (e.g. '*.png'). "
                    "Optional for: bulk-set."
                ),
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds",
                "default": 60,
            },
        },
        "required": ["operation"],
    }


def unity_lightmap_operation() -> dict[str, Any]:
    """Consolidated lightmap operation tool with operation dispatch."""
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "description": "Lightmap operation to perform",
                "enum": ["bake", "cancel", "clear", "status", "settings"],
            },
            "runAsync": {
                "type": "boolean",
                "description": (
                    "Return immediately (true) or wait for completion (false). "
                    "Only for 'bake' operation."
                ),
                "default": True,
            },
            "timeout": {
                "type": "integer",
                "description": (
                    "Timeout in seconds. Defaults to 30 for most operations, 3600 for sync bake."
                ),
            },
        },
        "required": ["operation"],
    }

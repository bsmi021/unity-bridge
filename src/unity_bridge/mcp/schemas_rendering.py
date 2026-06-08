"""MCP schemas for rendering and build-pipeline tools."""

from __future__ import annotations

from typing import Any


def render_pipeline() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": [
                    "list-assets",
                    "get-current",
                    "set-default",
                    "set-quality",
                    "inspect",
                ],
                "description": "Render pipeline operation",
            },
            "assetPath": {
                "type": "string",
                "description": "RenderPipelineAsset path, none, or builtin",
            },
            "qualityLevel": {
                "type": "string",
                "description": "Quality level name or index for set-quality",
            },
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds",
                "default": 15,
            },
        },
        "required": ["operation"],
    }


def graphics_state() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": [
                    "create",
                    "load-info",
                    "begin-trace",
                    "end-trace-save",
                    "warmup",
                    "clear-variants",
                ],
                "description": "GraphicsStateCollection operation",
            },
            "assetPath": {
                "type": "string",
                "description": "GraphicsStateCollection source path",
            },
            "outputPath": {
                "type": "string",
                "description": "GraphicsStateCollection output path",
            },
            "progressiveBatchSize": {
                "type": "integer",
                "description": "WarmUpProgressively batch size",
                "minimum": 1,
            },
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds",
                "default": 300,
            },
        },
        "required": ["operation"],
    }

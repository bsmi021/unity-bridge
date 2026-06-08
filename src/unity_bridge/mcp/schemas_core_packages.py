"""MCP schemas for Unity built-in package inspection tools."""

from __future__ import annotations

from typing import Any


def entities() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": [
                    "availability",
                    "list-worlds",
                    "world-summary",
                    "list-systems",
                    "list-archetypes",
                ],
                "description": "Unity Entities operation",
            },
            "worldName": {
                "type": "string",
                "description": "Entities world name. Defaults to the default world.",
            },
            "includeSystems": {
                "type": "boolean",
                "description": "Include system details with world summaries.",
                "default": False,
            },
            "includeComponents": {
                "type": "boolean",
                "description": "Include component type details with archetype summaries.",
                "default": False,
            },
            "namespaceFilter": {
                "type": "string",
                "description": "Optional namespace prefix filter for list-systems.",
            },
            "maxSystems": {
                "type": "integer",
                "description": "Maximum systems to return.",
                "minimum": 1,
            },
            "maxArchetypes": {
                "type": "integer",
                "description": "Maximum archetypes to return.",
                "minimum": 1,
            },
            "maxComponents": {
                "type": "integer",
                "description": "Maximum component types per archetype to return.",
                "minimum": 1,
            },
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds",
                "default": 15,
            },
        },
        "required": ["operation"],
    }


def adaptive_performance() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["availability", "settings", "list-profiles", "inspect-profile"],
                "description": "Adaptive Performance operation",
            },
            "assetPath": {
                "type": "string",
                "description": "AdaptivePerformanceScalerProfile asset path.",
            },
            "includeScalers": {
                "type": "boolean",
                "description": "Include scaler settings in profile results.",
                "default": False,
            },
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds",
                "default": 15,
            },
        },
        "required": ["operation"],
    }

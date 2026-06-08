"""MCP schemas for Unity 6.x Editor opportunity tools."""

from __future__ import annotations

from typing import Any


def object_identity() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["get-selection", "resolve", "ping"],
                "default": "resolve",
                "description": "Identity operation to run",
            },
            "gameObjectPath": {"type": "string", "description": "Scene hierarchy path"},
            "assetPath": {"type": "string", "description": "Unity asset path"},
            "globalObjectId": {"type": "string", "description": "Unity GlobalObjectId"},
            "instanceId": {"type": "integer", "description": "Legacy Unity instance ID"},
            "entityId": {"type": "string", "description": "Unity 6 EntityId string"},
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds",
                "default": 10,
            },
        },
        "required": ["operation"],
    }


def project_auditor() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["availability", "run", "load"],
                "default": "availability",
                "description": "Project Auditor operation",
            },
            "outputPath": {
                "type": "string",
                "description": "Report output path for run/load operations",
            },
            "maxIssues": {
                "type": "integer",
                "description": "Maximum issue rows to return",
                "default": 100,
                "minimum": 0,
                "maximum": 10000,
            },
            "categories": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Project Auditor issue categories to include",
            },
            "assemblyNames": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Assembly names to analyze",
            },
            "platform": {
                "type": "string",
                "description": "Unity BuildTarget name for analysis",
            },
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds",
                "default": 300,
            },
        },
        "required": ["operation"],
    }

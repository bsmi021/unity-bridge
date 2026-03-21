"""MCP tool input schemas for Unity Bridge (pipeline: build/platform gaps).

Schemas for script execution order, assembly reload lock, and find references.
"""

from __future__ import annotations

from typing import Any


def script_execution_order() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["get", "set"],
                "description": "Operation: get (list all) or set (one script)",
            },
            "scriptPath": {
                "type": "string",
                "description": "Asset path to the script (required for 'set')",
            },
            "order": {
                "type": "integer",
                "description": "Execution order value (required for 'set'). Negative = earlier.",
            },
            "nonDefaultOnly": {
                "type": "boolean",
                "description": "For 'get': only return scripts with non-zero execution order",
                "default": False,
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["operation"],
    }


def assembly_reload_lock() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["lock", "unlock", "status"],
                "description": "Lock, unlock, or check assembly reload lock status",
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["operation"],
    }


def find_references() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["find-in-scene"],
                "description": "Reference search operation",
            },
            "assetPath": {
                "type": "string",
                "description": "Asset path to search for references to",
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["operation", "assetPath"],
    }

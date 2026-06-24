"""MCP schemas for client-side operation ledger helpers."""

from __future__ import annotations

from typing import Any


def operation_status() -> dict[str, Any]:
    """Schema for reading durable operation state by command ID."""
    return {
        "type": "object",
        "properties": {
            "commandId": {
                "type": "string",
                "description": "Bridge command ID to inspect",
            },
        },
        "required": ["commandId"],
    }


def submit_command() -> dict[str, Any]:
    """Schema for queuing a Unity command without waiting for completion."""
    return {
        "type": "object",
        "properties": {
            "commandType": {
                "type": "string",
                "description": "Bridge command type to queue, e.g. query-hierarchy",
            },
            "parameters": {
                "type": "object",
                "description": "Bridge command parameters",
                "default": {},
            },
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds after dispatch starts",
                "default": 30,
            },
        },
        "required": ["commandType"],
    }

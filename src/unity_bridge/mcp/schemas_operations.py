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

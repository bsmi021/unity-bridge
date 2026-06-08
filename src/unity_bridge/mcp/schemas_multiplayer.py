"""MCP schemas for Unity Multiplayer package surfaces."""

from __future__ import annotations

from typing import Any


def multiplayer_playmode() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["availability", "current-player", "packages"],
                "description": "Multiplayer Play Mode operation",
            },
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds",
                "default": 15,
            },
        },
        "required": ["operation"],
    }

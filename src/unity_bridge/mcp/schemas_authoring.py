"""MCP schemas for authoring-system bridge tools."""

from __future__ import annotations

from typing import Any


def ui_toolkit() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": [
                    "list-documents",
                    "inspect-uxml",
                    "inspect-uss",
                    "create-uxml",
                    "create-panel-settings",
                    "add-ui-document",
                ],
                "description": "UI Toolkit operation",
            },
            "assetPath": {"type": "string", "description": "UXML/USS/asset path"},
            "gameObjectPath": {"type": "string", "description": "Scene object path"},
            "uxmlPath": {"type": "string", "description": "UXML asset path"},
            "ussPath": {"type": "string", "description": "USS asset path"},
            "panelSettingsPath": {
                "type": "string",
                "description": "PanelSettings asset path",
            },
            "sortingOrder": {"type": "integer", "description": "UIDocument sort order"},
            "maxDepth": {"type": "integer", "description": "Max visual tree depth"},
            "overwrite": {"type": "boolean", "default": False},
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds",
                "default": 15,
            },
        },
        "required": ["operation"],
    }

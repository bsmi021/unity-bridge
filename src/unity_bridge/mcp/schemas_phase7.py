"""MCP input schemas for Phase 7a (Query & Report) tools."""

from __future__ import annotations

from typing import Any


def sync_solution() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds",
                "default": 30,
            },
        },
    }


def cloud_services() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["get-project-id", "get-environments", "get-active-environment"],
                "description": "Cloud services lookup to run",
            },
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds",
                "default": 10,
            },
        },
        "required": ["operation"],
    }


def physics2d_config() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["get", "set", "get-collision-matrix", "set-collision"],
                "description": "Physics2D operation",
            },
            "setGravity": {"type": "boolean"},
            "gravityX": {"type": "number"},
            "gravityY": {"type": "number"},
            "setVelocityIterations": {"type": "boolean"},
            "velocityIterations": {"type": "integer"},
            "setPositionIterations": {"type": "boolean"},
            "positionIterations": {"type": "integer"},
            "setVelocityThreshold": {"type": "boolean"},
            "velocityThreshold": {"type": "number"},
            "setDefaultContactOffset": {"type": "boolean"},
            "defaultContactOffset": {"type": "number"},
            "setQueriesHitTriggers": {"type": "boolean"},
            "queriesHitTriggers": {"type": "boolean"},
            "setAutoSyncTransforms": {"type": "boolean"},
            "autoSyncTransforms": {"type": "boolean"},
            "layerA": {"type": "integer", "minimum": 0, "maximum": 31},
            "layerB": {"type": "integer", "minimum": 0, "maximum": 31},
            "collides": {"type": "boolean"},
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds",
                "default": 10,
            },
        },
        "required": ["operation"],
    }


def search_query() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["query", "providers"],
                "default": "query",
                "description": "Search operation",
            },
            "query": {
                "type": "string",
                "description": (
                    "Quick Search query string (e.g. 't:Material', "
                    "'p: com.unity.ui', 'h: Player')."
                ),
            },
            "maxResults": {
                "type": "integer",
                "description": "Maximum number of results to return",
                "default": 100,
                "minimum": 1,
                "maximum": 1000,
            },
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds",
                "default": 30,
            },
        },
    }

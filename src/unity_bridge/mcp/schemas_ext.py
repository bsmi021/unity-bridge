"""MCP tool input schemas for Unity Bridge (part 2: extensions).

Phase 1 schemas: asset-extended-operation, player-settings, package, build-profile.
Phase 2 schemas: undo, compilation-pipeline, prefab-overrides, list-tests, gameobject-utility.
Split from ``schemas.py`` to stay under 500 LOC.
"""

from __future__ import annotations

from typing import Any


def asset_extended() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": [
                    "create",
                    "delete",
                    "copy",
                    "move",
                    "deps",
                    "guid",
                    "folder-create",
                    "folder-list",
                    "export",
                    "import-package",
                    "reserialize",
                ],
                "description": "Extended asset operation to perform",
            },
            "assetPath": {
                "type": "string",
                "description": "Primary asset path (must start with Assets/)",
            },
            "sourcePath": {
                "type": "string",
                "description": "Source path for copy/move (must start with Assets/)",
            },
            "destinationPath": {
                "type": "string",
                "description": "Destination path for copy/move (must start with Assets/)",
            },
            "assetType": {
                "type": "string",
                "description": (
                    "Asset type for create operation (ScriptableObject, Material, "
                    "AnimatorController, etc.). Cannot create prefabs -- use prefab "
                    "command group instead."
                ),
            },
            "useTrash": {
                "type": "boolean",
                "description": "Move to trash instead of permanent delete",
                "default": False,
            },
            "recursive": {
                "type": "boolean",
                "description": "Include transitive dependencies (for deps operation)",
                "default": True,
            },
            "assetPaths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Multiple asset paths (for export)",
            },
            "outputPath": {
                "type": "string",
                "description": "Output file path (for export)",
            },
            "includeDependencies": {
                "type": "boolean",
                "description": "Include dependencies in export",
                "default": True,
            },
            "interactive": {
                "type": "boolean",
                "description": "Show import dialog (for import-package)",
                "default": False,
            },
            "input": {
                "type": "string",
                "description": "Path or GUID input (for guid operation)",
            },
            "folderPath": {
                "type": "string",
                "description": "Folder path (for folder operations)",
            },
            "packagePath": {
                "type": "string",
                "description": "Path to .unitypackage file (for import-package)",
            },
            "reserializeMode": {
                "type": "string",
                "enum": ["assets", "metadata", "both"],
                "description": "Reserialize mode (for reserialize operation)",
            },
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds",
                "default": 60,
            },
        },
        "required": ["operation"],
    }


def player_settings() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["get", "set", "defines-list", "defines-add", "defines-remove"],
                "description": "Player settings operation to perform",
            },
            "key": {
                "type": "string",
                "description": "Setting key for get/set (e.g. companyName, productName, bundleVersion)",
            },
            "value": {
                "type": "string",
                "description": "New value for set operation",
            },
            "symbol": {
                "type": "string",
                "description": "Define symbol (required for defines-add/defines-remove)",
            },
            "platform": {
                "type": "string",
                "description": (
                    "Named build target (default: active platform). "
                    "Common values: Standalone, Android, iOS, WebGL, Server, "
                    "WindowsStoreApps. The C# handler's platform map is the "
                    "source of truth for validation."
                ),
            },
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds",
                "default": 15,
            },
        },
        "required": ["operation"],
    }


def package_operation() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": [
                    "list",
                    "search",
                    "search-all",
                    "add",
                    "remove",
                    "info",
                    "embed",
                    "resolve",
                ],
                "description": "Package manager operation to perform",
            },
            "identifier": {
                "type": "string",
                "description": "Package identifier (name@version or git URL) for add",
            },
            "packageName": {
                "type": "string",
                "description": "Package name for remove/embed/info",
            },
            "query": {
                "type": "string",
                "description": (
                    "Package ID or name to search for (search operation). "
                    "Searches by package ID/name, not free-text keywords."
                ),
            },
            "source": {
                "type": "string",
                "enum": ["registry", "git", "embedded", "local"],
                "description": "Filter by package source type (list operation)",
            },
            "offlineMode": {
                "type": "boolean",
                "description": "Use offline mode for list (cached data only)",
                "default": False,
            },
            "includeIndirectDependencies": {
                "type": "boolean",
                "description": "Include indirect (transitive) dependencies in list results",
                "default": False,
            },
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds",
                "default": 60,
            },
        },
        "required": ["operation"],
    }


def build_profile() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["list", "get-active", "set-active", "get-info"],
                "description": "Build profile operation to perform",
            },
            "profilePath": {
                "type": "string",
                "description": "Asset path to build profile (for set-active, get-info)",
            },
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds",
                "default": 30,
            },
        },
        "required": ["operation"],
    }


# ---------------------------------------------------------------------------
# Phase 2 schemas
# ---------------------------------------------------------------------------


def undo_operation() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": [
                    "perform",
                    "redo",
                    "history",
                    "clear",
                    "group-name",
                    "collapse",
                ],
                "description": "Undo operation to perform",
            },
            "limit": {
                "type": "integer",
                "description": "Max history entries (for 'history' operation)",
                "default": 20,
            },
            "groupIndex": {
                "type": "integer",
                "description": "Undo group index to collapse from (for 'collapse' operation)",
            },
            "name": {
                "type": "string",
                "description": "Name for the collapsed undo group (for 'collapse' operation)",
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["operation"],
    }


def compilation_pipeline() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["assemblies", "defines", "which", "optimization"],
                "description": "Pipeline query to perform",
            },
            "assemblyName": {
                "type": "string",
                "description": "Assembly name (for 'defines' operation)",
            },
            "scriptPath": {
                "type": "string",
                "description": "Script asset path (for 'which' operation)",
            },
            "mode": {
                "type": "string",
                "enum": ["None", "Debug", "Release"],
                "description": (
                    "Optimization mode to set (for 'optimization' operation). "
                    "None = not set / use project default."
                ),
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["operation"],
    }


def prefab_overrides() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": [
                    "list",
                    "apply",
                    "revert",
                    "status",
                    "find-instances",
                    "unpack",
                ],
                "description": "Prefab override operation",
            },
            "instancePath": {
                "type": "string",
                "description": "Hierarchy path to prefab instance",
            },
            "assetPath": {
                "type": "string",
                "description": "Prefab asset path (for 'find-instances')",
            },
            "target": {
                "type": "string",
                "description": "Specific override to apply/revert (omit for all)",
            },
            "completely": {
                "type": "boolean",
                "description": "Fully unpack nested prefabs (for 'unpack')",
                "default": False,
            },
            "includeDefaultOverrides": {
                "type": "boolean",
                "description": ("Include default overrides like position/rotation (for 'list')"),
                "default": False,
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["operation"],
    }


def list_tests() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "enum": ["tests", "categories", "assemblies"],
                "description": "What to list",
                "default": "tests",
            },
            "testPlatform": {
                "type": "string",
                "enum": ["EditMode", "PlayMode"],
                "description": "Test platform filter",
            },
            "filter": {
                "type": "string",
                "description": "Test name filter pattern",
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
    }


def gameobject_utility() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": [
                    "missing-scripts",
                    "static-flags",
                    "set-static-flags",
                    "set-layer",
                    "set-tag",
                    "duplicate",
                ],
                "description": "Utility operation",
            },
            "gameObjectPath": {
                "type": "string",
                "description": "Hierarchy path to target GameObject",
            },
            "fix": {
                "type": "boolean",
                "description": "Remove missing scripts (for 'missing-scripts')",
                "default": False,
            },
            "flags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Static flags to set",
            },
            "layer": {
                "type": "integer",
                "description": "Layer index (for 'set-layer')",
            },
            "tag": {
                "type": "string",
                "description": "Tag name (for 'set-tag')",
            },
            "recursive": {
                "type": "boolean",
                "description": ("Apply to children, including inactive children (for 'set-layer')"),
                "default": False,
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["operation"],
    }


def batch() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "commands": {
                "type": "array",
                "description": "Array of commands to execute",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Optional identifier"},
                        "type": {"type": "string", "description": "Command type"},
                        "parameters": {"type": "object", "description": "Command parameters"},
                    },
                    "required": ["type"],
                },
            },
            "stopOnError": {
                "type": "boolean",
                "description": "Stop execution if any command fails",
                "default": True,
            },
            "parallel": {
                "type": "boolean",
                "description": "Execute read-only commands in parallel",
                "default": False,
            },
        },
        "required": ["commands"],
    }


def help_topic() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "enum": ["commands", "workflows", "troubleshooting", "examples"],
                "description": "Help topic",
                "default": "commands",
            },
            "command": {"type": "string", "description": "Specific command to get help for"},
        },
    }

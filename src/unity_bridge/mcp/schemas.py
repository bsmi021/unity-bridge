"""MCP tool input schemas for Unity Bridge (part 1: core operations).

Each function returns a JSON Schema ``dict`` identical to the schemas in
the legacy ``unity_bridge_mcp_server.py``.  Split across two files
(``schemas.py`` and ``schemas_ext.py``) to stay under 500 LOC.
"""

from __future__ import annotations

from typing import Any


def run_tests() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "testPlatform": {
                "type": "string",
                "enum": ["EditMode", "PlayMode"],
                "description": "Test platform to execute",
            },
            "testFilter": {
                "type": "string",
                "description": "Optional test filter pattern (e.g., 'CombatTests')",
            },
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds",
                "default": 300,
            },
        },
        "required": ["testPlatform"],
    }


def query_hierarchy() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "maxDepth": {
                "type": "integer",
                "description": "Maximum hierarchy depth to traverse",
                "default": 5,
            },
            "includeInactive": {
                "type": "boolean",
                "description": "Include inactive GameObjects",
                "default": False,
            },
            "rootPath": {
                "type": "string",
                "description": "Optional root GameObject path to start from",
            },
        },
    }


def get_component_data() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "gameObjectPath": {"type": "string", "description": "Path to GameObject in hierarchy"},
            "componentType": {"type": "string", "description": "Fully qualified component type"},
            "fieldNames": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional field names to retrieve",
            },
        },
        "required": ["gameObjectPath", "componentType"],
    }


def set_component_data() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "gameObjectPath": {"type": "string", "description": "Path to GameObject in hierarchy"},
            "componentType": {"type": "string", "description": "Fully qualified component type"},
            "fieldUpdates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "fieldName": {"type": "string"},
                        "valueJson": {"type": "string"},
                    },
                    "required": ["fieldName", "valueJson"],
                },
                "description": "List of field updates with JSON-encoded values",
            },
        },
        "required": ["gameObjectPath", "componentType", "fieldUpdates"],
    }


def add_component() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "gameObjectPath": {"type": "string", "description": "Path to GameObject in hierarchy"},
            "componentType": {
                "type": "string",
                "description": "Fully qualified component type to add",
            },
        },
        "required": ["gameObjectPath", "componentType"],
    }


def validate_prefab() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "prefabPath": {"type": "string", "description": "Path to prefab asset"},
            "checkMissingReferences": {
                "type": "boolean",
                "description": "Check for missing or null references",
                "default": True,
            },
        },
        "required": ["prefabPath"],
    }


def scene_operation() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["load", "create", "save"],
                "description": "Scene operation to perform",
            },
            "scenePath": {"type": "string", "description": "Path to scene file"},
            "saveCurrentScene": {
                "type": "boolean",
                "description": "Save current scene before loading new one",
                "default": False,
            },
        },
        "required": ["operation"],
    }


def prefab_operation() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["instantiate", "delete", "update"],
                "description": "Prefab operation",
            },
            "sourcePath": {"type": "string", "description": "Path to prefab asset"},
            "targetPath": {"type": "string", "description": "Target GameObject path"},
            "position": {
                "type": "object",
                "properties": {
                    "x": {"type": "number"},
                    "y": {"type": "number"},
                    "z": {"type": "number"},
                },
                "description": "Position for instantiated prefab",
            },
        },
        "required": ["operation"],
    }


def playmode_control() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["play", "pause", "stop"],
                "description": "Play mode operation",
            },
        },
        "required": ["operation"],
    }


def read_console() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "logTypes": {
                "type": "array",
                "items": {"type": "string", "enum": ["Error", "Warning", "Log"]},
                "description": "Types of logs to retrieve",
            },
            "maxEntries": {
                "type": "integer",
                "description": "Maximum log entries to retrieve",
                "default": 50,
            },
            "searchPattern": {
                "type": "string",
                "description": "Optional regex pattern to filter logs",
            },
            "includeStackTrace": {
                "type": "boolean",
                "description": "Include stack trace in output",
                "default": True,
            },
            "maxStackTraceLines": {
                "type": "integer",
                "description": "Max stack trace lines per entry (0=unlimited, -1=none)",
                "default": 5,
            },
            "maxMessageLength": {
                "type": "integer",
                "description": "Max characters for message text (0=unlimited)",
                "default": 500,
            },
        },
    }


def capture_screenshot() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "camera": {
                "type": "string",
                "description": "Camera name to capture from",
                "default": "Main Camera",
            },
            "resolution": {
                "type": "object",
                "properties": {"width": {"type": "integer"}, "height": {"type": "integer"}},
                "description": "Screenshot resolution",
            },
            "outputPath": {"type": "string", "description": "Screenshot output path"},
        },
        "required": ["outputPath"],
    }


def profiler_sample() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "includeMemory": {
                "type": "boolean",
                "description": "Include memory statistics",
                "default": True,
            },
            "includeRendering": {
                "type": "boolean",
                "description": "Include rendering statistics",
                "default": True,
            },
            "includeCPU": {
                "type": "boolean",
                "description": "Include CPU timing statistics",
                "default": False,
            },
        },
    }


def material_operation() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["modify", "create", "duplicate"],
                "description": "Material operation",
            },
            "materialPath": {"type": "string", "description": "Path to material asset"},
            "properties": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}, "value": {"type": "object"}},
                },
                "description": "Material properties to modify",
            },
        },
        "required": ["operation", "materialPath"],
    }


def asset_operation() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["find", "query", "import", "refresh"],
                "description": "Asset operation",
            },
            "assetPath": {"type": "string", "description": "Asset path or search directory"},
            "assetType": {"type": "string", "description": "Asset type filter"},
            "searchPattern": {"type": "string", "description": "Search pattern for finding assets"},
        },
        "required": ["operation"],
    }


def build_operation() -> dict[str, Any]:
    _targets = [
        "StandaloneWindows64",
        "StandaloneWindows",
        "StandaloneLinux64",
        "StandaloneOSX",
        "Android",
        "iOS",
        "WebGL",
    ]
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["build", "validate"],
                "description": "Build operation",
            },
            "target": {"type": "string", "enum": _targets, "description": "Build target platform"},
            "outputPath": {"type": "string", "description": "Build output path"},
            "development": {
                "type": "boolean",
                "description": "Create development build",
                "default": False,
            },
            "timeout": {
                "type": "integer",
                "description": "Build timeout in seconds",
                "default": 600,
            },
        },
        "required": ["operation", "target"],
    }


def animator_operation() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["setState", "setParameter", "getState", "getParameters"],
                "description": "Animator operation",
            },
            "gameObjectPath": {"type": "string", "description": "Path to GameObject with Animator"},
            "stateName": {"type": "string", "description": "Animator state name"},
            "parameterName": {"type": "string", "description": "Animator parameter name"},
            "parameterValue": {"description": "Parameter value (type depends on parameter type)"},
            "layerIndex": {"type": "integer", "description": "Animator layer index", "default": 0},
        },
        "required": ["operation", "gameObjectPath"],
    }


def bridge_config() -> dict[str, Any]:
    _levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "OFF"]
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["get_log_level", "set_log_level", "get_config"],
                "description": "Configuration operation",
            },
            "log_level": {"type": "string", "enum": _levels, "description": "Logging level to set"},
        },
        "required": ["operation"],
    }


def clear_console() -> dict[str, Any]:
    return {"type": "object", "properties": {}, "required": []}


def get_selection() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "includeComponents": {
                "type": "boolean",
                "description": "Include component list for each selected object",
                "default": False,
            },
            "includeChildren": {
                "type": "boolean",
                "description": "Include child objects in selection",
                "default": False,
            },
        },
    }


def refresh_assets() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "forceUpdate": {
                "type": "boolean",
                "description": "Force reimport even if assets appear unchanged",
                "default": False,
            },
        },
    }


def focus_object() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "gameObjectPath": {"type": "string", "description": "Path to GameObject in hierarchy"},
            "frameSelection": {
                "type": "boolean",
                "description": "Frame the object (zoom to fit)",
                "default": True,
            },
        },
        "required": ["gameObjectPath"],
    }


def health_check() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "waitForHealthy": {
                "type": "boolean",
                "description": "Wait for Unity to become healthy (up to 30s)",
                "default": False,
            },
        },
    }


def compile_scripts() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "waitForCompletion": {
                "type": "boolean",
                "description": "Wait for compilation to complete",
                "default": True,
            },
            "timeout": {
                "type": "integer",
                "description": "Maximum wait for compilation (seconds)",
                "default": 120,
            },
        },
    }


def execute_menu_item() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "menuPath": {
                "type": "string",
                "description": "Full menu path (e.g., 'GameObject/Create Empty')",
            },
            "validate": {
                "type": "boolean",
                "description": "Check if menu item exists without executing",
                "default": False,
            },
        },
        "required": ["menuPath"],
    }


# batch() and help_topic() moved to schemas_ext.py to stay under 500 LOC.

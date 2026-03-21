"""
Command protocol types, timeout defaults, and parallel-safe commands.

Extracted from unity_bridge_mcp_server.py. This module defines the
canonical timeout values and the set of commands safe for parallel
execution in batch mode.
"""

# Smart timeout defaults by command type (seconds).
# Quick operations use 5-15s, medium 30s, long 60-300s, very long 600s.
TIMEOUT_DEFAULTS: dict[str, int] = {
    # Quick operations
    "query-hierarchy": 10,
    "get-component-data": 10,
    "read-console": 10,
    "playmode-control": 10,
    "clear-console": 5,
    "get-selection": 5,
    "refresh-assets": 15,
    "focus-object": 5,
    "health-check": 5,
    # Medium operations
    "set-component-data": 30,
    "add-component": 30,
    "scene-operation": 30,
    "prefab-operation": 30,
    "validate-prefab": 30,
    "material-operation": 30,
    "animator-operation": 30,
    "execute-menu-item": 30,
    "execute-script": 30,
    # Long operations
    "run-tests": 300,
    "compile": 120,
    "asset-operation": 60,
    "asset-extended-operation": 60,
    "package-operation": 60,
    "player-settings-operation": 15,
    "build-profile-operation": 30,
    # Very long operations
    "build-operation": 600,
    # Phase 2: Undo (quick, read-only or instant)
    "undo-operation": 5,
    # Phase 2: Compilation pipeline (read-heavy, optimization set is fast)
    "compilation-pipeline": 15,
    # Phase 2: Prefab overrides (mutating)
    "prefab-override": 30,
    # Phase 2: Test listing (may wait for test framework)
    "list-tests": 30,
    # Phase 2: GameObject utilities (mixed read/write)
    "gameobject-utility": 15,
    # Phase 3: Shader inspection (read-only, fast)
    "shader-inspection": 15,
    # Phase 3: Lightmap operations (varies widely; bake sync overrides to 3600)
    "lightmap-operation": 30,
    # Phase 3: Scene setup (medium — restore loads scenes)
    "scene-setup-operation": 30,
    # Phase 3: Import settings (medium — reimport can take time)
    "import-settings-operation": 60,
    # Phase 4: Set selection (quick)
    "set-selection": 5,
    # Phase 4: Editor prefs (quick, read/write)
    "editor-prefs": 5,
    # Phase 4: Build scenes (quick, mutating)
    "build-scenes": 15,
    # Phase 4: Transform (quick read, medium write)
    "transform-operation": 10,
    # Phase 4: Serialized property (quick read, medium write)
    "serialized-property": 15,
    # Phase 4: Physics config (quick read/write)
    "physics-config": 10,
    # Phase 4: Quality settings (quick read/write)
    "quality-settings": 10,
    # Phase 4: Tags/layers (quick read, medium write)
    "tags-layers": 15,
    # Phase 4: Editor config (quick read/write)
    "editor-config": 10,
    # Phase 5: Quick wins
    "remove-component": 15,
    "component-toggle": 10,
    "console-log": 5,
    # Phase 4 expansion: Build, Platform, Pipeline
    "script-execution-order": 15,
    "assembly-reload-lock": 5,
    "find-references": 30,
    # Phase 4 Misc: Expanded capabilities
    "clipboard": 5,
    "preset-operation": 15,
    "scene-template": 30,
    "script-info": 15,
    "deep-serialize": 10,
    "window-management": 5,
    "input-system": 15,
}

# Commands that are safe for parallel execution in batch mode.
# These are all read-only operations that do not mutate Unity state.
PARALLEL_SAFE_COMMANDS: set[str] = {
    "query-hierarchy",
    "get-component-data",
    "get-selection",
    "read-console",
    "validate-prefab",
    "health-check",
    "list-tests",
    "shader-inspection",
    "transform-operation",  # get operation is read-only
    "serialized-property",  # list/get operations are read-only
    "script-execution-order",  # get operation is read-only
    "find-references",  # find-in-scene is read-only
    "clipboard",  # read operation is read-only
    "script-info",  # info/list are read-only
    "deep-serialize",  # get operation is read-only
    "window-management",  # list operation is read-only
    "input-system",  # list-actions/get-action-map/export are read-only
}

# Default timeout when command type is not in TIMEOUT_DEFAULTS.
_FALLBACK_TIMEOUT: int = 30


def get_timeout(
    command_type: str,
    command_override: int | None = None,
    global_override: int | None = None,
) -> int:
    """Resolve timeout with precedence.

    Priority: command-specific override > global override > per-command default.

    Args:
        command_type: Bridge command type for TIMEOUT_DEFAULTS lookup.
        command_override: Timeout from a command-level --timeout flag.
        global_override: Timeout from the global --timeout flag.

    Returns:
        Resolved timeout in seconds.
    """
    if command_override is not None:
        return command_override
    if global_override is not None:
        return global_override
    return TIMEOUT_DEFAULTS.get(command_type, _FALLBACK_TIMEOUT)


def is_parallel_safe(command_type: str) -> bool:
    """Return True if the command is safe for parallel batch execution."""
    return command_type in PARALLEL_SAFE_COMMANDS

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
    # Very long operations
    "build-operation": 600,
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

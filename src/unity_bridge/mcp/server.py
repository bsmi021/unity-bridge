"""MCP server for Unity Bridge.

Migrated from ``unity_bridge_mcp_server.py``.  Uses the same core async
functions as the CLI so behaviour is always identical.

Start via ``unity-bridge serve`` or ``python -m unity_bridge.mcp.server``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

from unity_bridge.commands.batch import batch_execute
from unity_bridge.commands.diagnostics import status as diagnostics_status
from unity_bridge.core.bridge import DirectBridge
from unity_bridge.core.cache import get_cache
from unity_bridge.core.config import BridgeConfig, load_config_file, save_config_file
from unity_bridge.core.project import detect_unity_project
from unity_bridge.core.protocol import get_timeout
from unity_bridge.core.retry import RetryConfig
from unity_bridge.mcp.tools import TOOL_COMMAND_MAP, TOOL_DEFINITIONS

logger = logging.getLogger("unity_bridge")

# Help content for the unity_help tool
_HELP_CONTENT: dict[str, str] = {
    "commands": (
        "# Unity Bridge Commands\n\n"
        "## Testing\n"
        "- `unity_run_tests` - Execute EditMode or PlayMode tests\n"
        "- `unity_compile` - Trigger compilation and get errors\n\n"
        "## Hierarchy\n"
        "- `unity_query_hierarchy` - Inspect GameObject hierarchy\n"
        "- `unity_get_selection` - Get selected objects\n"
        "- `unity_focus_object` - Focus on a GameObject\n\n"
        "## Components\n"
        "- `unity_get_component_data` - Read component values\n"
        "- `unity_set_component_data` - Modify component values\n"
        "- `unity_add_component` - Add component to GameObject\n\n"
        "## Scenes & Prefabs\n"
        "- `unity_scene_operation` - Load/save/create scenes\n"
        "- `unity_prefab_operation` - Instantiate/manage prefabs\n"
        "- `unity_validate_prefab` - Check prefab integrity\n\n"
        "## Assets\n"
        "- `unity_asset_operation` - Find and query assets\n"
        "- `unity_refresh_assets` - Refresh asset database\n"
        "- `unity_material_operation` - Modify materials\n\n"
        "## Editor Control\n"
        "- `unity_playmode_control` - Play/pause/stop\n"
        "- `unity_execute_menu_item` - Execute any menu command\n"
        "- `unity_clear_console` - Clear console logs\n"
        "- `unity_read_console` - Read console logs\n\n"
        "## Diagnostics\n"
        "- `unity_health_check` - Check bridge health\n"
        "- `unity_profiler_sample` - Capture performance metrics\n"
        "- `unity_capture_screenshot` - Take screenshots\n\n"
        "## Utility\n"
        "- `unity_batch` - Execute multiple commands\n"
        "- `unity_help` - This help command\n"
        "- `unity_bridge_config` - Configure logging"
    ),
    "workflows": (
        "# Common Workflows\n\n"
        "## TDD Workflow\n"
        "1. Edit code\n"
        "2. `unity_compile` - Check for errors\n"
        "3. `unity_run_tests` - Run tests\n"
        "4. `unity_read_console` - Check for runtime errors"
    ),
    "troubleshooting": (
        "# Troubleshooting\n\n"
        "## Unity Bridge Not Responding\n"
        "1. Check `unity_health_check` output\n"
        "2. Verify Unity is open and not frozen\n"
        "3. Try `unity_refresh_assets` to trigger update"
    ),
    "examples": (
        "# Example Commands\n\n"
        "## Run All EditMode Tests\n"
        "```\nunity_run_tests(testPlatform=\"EditMode\")\n```\n\n"
        "## Check for Compilation Errors\n"
        "```\nunity_compile(waitForCompletion=true)\n```"
    ),
}

# Valid logging levels
_VALID_LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
    "OFF": logging.CRITICAL + 10,
}

# ---------------------------------------------------------------------------
# Bridge singleton
# ---------------------------------------------------------------------------

_bridge_instance: DirectBridge | None = None


def _get_bridge(project_root: Path) -> DirectBridge:
    """Return or create the shared DirectBridge instance."""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = DirectBridge(project_root)
    return _bridge_instance


# ---------------------------------------------------------------------------
# Core command invocation
# ---------------------------------------------------------------------------


async def _invoke_command(
    project_root: Path,
    command_type: str,
    parameters: dict[str, Any] | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    """Execute a Unity Bridge command via DirectBridge with caching."""
    if parameters is None:
        parameters = {}

    # Check cache
    try:
        cache = get_cache()
        cached = await cache.get(command_type, parameters)
        if cached is not None:
            cached["cached"] = True
            return cached
    except Exception:
        logger.debug("Cache read failed for %s", command_type, exc_info=True)

    bridge = _get_bridge(project_root)
    try:
        result = await bridge.send_command_with_retry(
            command_type=command_type,
            parameters=parameters,
            timeout=float(timeout),
            retry_config=RetryConfig(max_retries=3, base_delay=0.1),
        )
    except Exception as exc:
        return {"success": False, "status": "error", "error": str(exc)}

    result_dict = result.to_dict()

    # Cache successful results
    if result.success:
        try:
            cache = get_cache()
            await cache.set(command_type, parameters, result_dict)
        except Exception:
            logger.debug("Cache write failed for %s", command_type, exc_info=True)

    return result_dict


# ---------------------------------------------------------------------------
# Special tool handlers (Python-side, no Unity command)
# ---------------------------------------------------------------------------


async def _handle_config(
    arguments: dict[str, Any],
    config_file: Path,
) -> dict[str, Any]:
    """Handle unity_bridge_config tool."""
    operation = arguments.get("operation", "get_config")
    if operation == "get_log_level":
        cfg = load_config_file(config_file)
        return {
            "success": True,
            "log_level": cfg.get("log_level", "INFO"),
            "valid_levels": list(_VALID_LOG_LEVELS.keys()),
        }
    if operation == "set_log_level":
        level = arguments.get("log_level", "INFO").upper()
        if level not in _VALID_LOG_LEVELS:
            return {"success": False, "error": f"Invalid log level: {level}"}
        cfg = load_config_file(config_file)
        cfg["log_level"] = level
        saved = save_config_file(cfg, config_file)
        # Apply level to the live logger immediately
        logging.getLogger("unity_bridge").setLevel(_VALID_LOG_LEVELS[level])
        return {
            "success": True,
            "log_level": level,
            "persisted": saved,
            "message": f"Log level set to {level}",
        }
    if operation == "get_config":
        cfg = load_config_file(config_file)
        return {
            "success": True,
            "config": cfg,
            "config_file": str(config_file),
            "valid_log_levels": list(_VALID_LOG_LEVELS.keys()),
        }
    return {"success": False, "error": f"Unknown operation: {operation}"}


async def _handle_help(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle unity_help tool."""
    topic = arguments.get("topic", "commands")
    command_name = arguments.get("command")
    if command_name:
        return {
            "success": True,
            "command": command_name,
            "help": f"Use unity_{command_name.replace('-', '_')} tool.",
        }
    content = _HELP_CONTENT.get(topic, _HELP_CONTENT["commands"])
    return {"success": True, "topic": topic, "help": content}


async def _handle_health_check(
    arguments: dict[str, Any],
    project_root: Path,
) -> dict[str, Any]:
    """Handle unity_health_check tool via shared diagnostics.status()."""
    wait = arguments.get("waitForHealthy", False)
    if wait:
        # wait_for_healthy is MCP-specific; not in the shared status() path
        from unity_bridge.core.health import HealthMonitor
        try:
            monitor = HealthMonitor(project_root)
            health = monitor.wait_for_healthy(timeout_seconds=30.0)
            return {"success": True, "health": health.to_dict()}
        except Exception as exc:
            return {"success": True, "health": {"healthy": False, "reason": str(exc)}}

    result = await diagnostics_status(project_root)
    result_dict = result.to_dict()
    return {"success": result_dict["success"], "health": result_dict.get("data", {})}


async def _handle_batch(
    arguments: dict[str, Any],
    project_root: Path,
) -> dict[str, Any]:
    """Handle unity_batch tool via shared batch_execute()."""
    commands = arguments.get("commands", [])
    stop_on_error = arguments.get("stopOnError", True)
    parallel = arguments.get("parallel", False)

    bridge = _get_bridge(project_root)
    result = await batch_execute(bridge, commands, stop_on_error, parallel)
    return result.to_dict()


# ---------------------------------------------------------------------------
# Server entry point
# ---------------------------------------------------------------------------


async def _auto_install_bridge() -> None:
    """Auto-install or update the C# bridge files on startup."""
    from unity_bridge.commands.lifecycle import install

    result = await install()
    if result.success:
        action = result.data.get("action", "unknown") if result.data else "unknown"
        ver = result.data.get("version", "unknown") if result.data else "unknown"
        if action == "install":
            logger.info("Bridge installed (v%s)", ver)
        elif action == "update":
            logger.info("Bridge updated to v%s", ver)
        else:
            logger.debug("Bridge up to date (v%s)", ver)
    else:
        logger.warning("Bridge install warning: %s", result.error or "unknown")


async def run_mcp_server(config: BridgeConfig | None = None) -> None:
    """Start MCP server with stdio transport."""
    try:
        from mcp.server import Server
        from mcp.types import Tool, TextContent
        from mcp.server.stdio import stdio_server
    except ImportError:
        print(
            "Error: MCP SDK not found. Install with: pip install mcp",
            file=sys.stderr,
        )
        sys.exit(1)

    if config is None:
        config = BridgeConfig.from_env()

    project_root = config.project_root or detect_unity_project()
    config_file = config.config_file or (project_root / "unity_bridge_config.json")

    await _auto_install_bridge()

    server = Server("unity-bridge")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name=td["name"],
                description=td["description"],
                inputSchema=td["inputSchema"],
            )
            for td in TOOL_DEFINITIONS
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Any) -> list[TextContent]:
        args = arguments if isinstance(arguments, dict) else {}
        result = await _dispatch(name, args, project_root, config_file)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    logger.info("MCP server starting (project: %s)", project_root)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


async def _dispatch(
    name: str,
    arguments: dict[str, Any],
    project_root: Path,
    config_file: Path,
) -> dict[str, Any]:
    """Route an MCP tool call to the appropriate handler."""
    if name == "unity_bridge_config":
        return await _handle_config(arguments, config_file)
    if name == "unity_help":
        return await _handle_help(arguments)
    if name == "unity_health_check":
        return await _handle_health_check(arguments, project_root)
    if name == "unity_batch":
        return await _handle_batch(arguments, project_root)

    command_type = TOOL_COMMAND_MAP.get(name)
    if not command_type:
        return {"success": False, "error": f"Unknown tool: {name}"}

    timeout = arguments.pop("timeout", None)
    resolved_timeout = get_timeout(command_type, command_override=timeout)
    return await _invoke_command(project_root, command_type, arguments, resolved_timeout)


# ---------------------------------------------------------------------------
# Direct execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(run_mcp_server())

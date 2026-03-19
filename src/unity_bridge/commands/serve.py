"""Serve command: start the MCP server for Claude Code integration."""

from __future__ import annotations

import asyncio

import typer

# ---------------------------------------------------------------------------
# Core function
# ---------------------------------------------------------------------------


def start_mcp_server(
    project_root: str | None = None,
    log_level: str = "ERROR",
) -> None:
    """Start the MCP server using stdio transport.

    This function imports and runs the MCP server module, passing through
    any configuration. It is the implementation behind ``unity-bridge serve``.

    Args:
        project_root: Optional Unity project root override.
        log_level: Logging level for the server.
    """
    import sys
    import os

    # Ensure the legacy module is importable (lives alongside this package)
    plugin_dir = _find_plugin_dir()
    if plugin_dir is not None and str(plugin_dir) not in sys.path:
        sys.path.insert(0, str(plugin_dir))

    # Set environment variables for the server to pick up
    if project_root is not None:
        os.environ["UNITY_BRIDGE_PROJECT"] = project_root
    os.environ.setdefault("UNITY_BRIDGE_LOG_LEVEL", log_level)

    try:
        from unity_bridge_mcp_server import main as mcp_main
        asyncio.run(mcp_main())
    except ImportError:
        _run_packaged_server()


def _find_plugin_dir() -> str | None:
    """Locate the unity-plugin/unity/ directory for legacy imports."""
    from pathlib import Path

    # Walk up from this file to find unity_bridge_mcp_server.py
    current = Path(__file__).resolve().parent
    for _ in range(6):
        candidate = current / "unity_bridge_mcp_server.py"
        if candidate.is_file():
            return str(current)
        current = current.parent
    return None


def _run_packaged_server() -> None:
    """Fallback: start MCP server from the packaged mcp module."""
    try:
        from unity_bridge.mcp.server import run_mcp_server
        asyncio.run(run_mcp_server())
    except ImportError as exc:
        raise SystemExit(
            f"Cannot start MCP server: {exc}. "
            "Ensure unity_bridge_mcp_server.py is on the Python path "
            "or install the unity-bridge[mcp] extra."
        ) from exc


# ---------------------------------------------------------------------------
# Typer CLI wrapper
# ---------------------------------------------------------------------------

serve_app = typer.Typer(name="serve", help="Start MCP server mode.")


@serve_app.callback(invoke_without_command=True)
def serve_cli(ctx: typer.Context) -> None:
    """Start MCP server mode for Claude Code integration."""
    state = ctx.obj
    project_str = str(state.config.project_root) if state.config.project_root else None
    log_level = state.config.log_level
    start_mcp_server(project_root=project_str, log_level=log_level)

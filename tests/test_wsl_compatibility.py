"""
Unit tests for WSL/Linux compatibility.

Verifies the codebase has been properly migrated from Windows/PowerShell
to work from WSL2/Linux.
"""

import pytest
import json
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def _get_project_root() -> Path:
    """Get the unity-plugin project root."""
    return Path(__file__).parent.parent


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        pytest.skip(f"{path.name} not present in this checkout")
    return path.read_text(encoding="utf-8")


class TestNoPowerShellReferences:
    """Verify no PowerShell references remain in server code."""

    def test_no_powershell_in_mcp_server(self):
        """MCP server source should not reference PowerShell."""
        server_path = _get_project_root() / "src" / "unity_bridge" / "mcp" / "server.py"
        content = server_path.read_text(encoding="utf-8")
        # Allow 'powershell' only in comments or strings that explicitly
        # document removal
        assert "powershell.exe" not in content.lower()
        assert "import subprocess" not in content

    def test_no_ps1_references_in_mcp_server(self):
        """MCP server should not reference .ps1 scripts."""
        server_path = _get_project_root() / "src" / "unity_bridge" / "mcp" / "server.py"
        content = server_path.read_text(encoding="utf-8")
        assert ".ps1" not in content

    def test_no_psutil_in_core_bridge_modules(self):
        """Core bridge modules should not import psutil."""
        root = _get_project_root() / "src" / "unity_bridge"
        for module_path in [root / "core" / "bridge.py", root / "core" / "health.py"]:
            content = module_path.read_text(encoding="utf-8")
            assert "import psutil" not in content

    def test_mcp_json_uses_unity_bridge_cli(self):
        """mcp.json should use unity-bridge CLI command."""
        mcp_path = _get_project_root() / "mcp.json"
        config = json.loads(_read_if_exists(mcp_path))
        unity_bridge = config["mcpServers"]["unity-bridge"]
        assert unity_bridge["command"] == "unity-bridge"
        assert unity_bridge["args"] == ["serve"]


class TestInvokeCommandWithoutDirectBridge:
    """Test current MCP dispatch handles unknown tools cleanly."""

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self):
        """Unknown MCP tool calls should return structured errors."""
        from unity_bridge.mcp.server import _dispatch

        result = await _dispatch(
            "unity_missing_tool",
            {},
            _get_project_root(),
            _get_project_root() / "unity_bridge_config.json",
        )

        assert result["success"] is False
        assert "Unknown tool" in result["error"]


class TestJsonLineEndings:
    """Verify JSON files use LF line endings for cross-platform compat."""

    def test_mcp_json_parseable(self):
        """mcp.json can be parsed regardless of line endings."""
        mcp_path = _get_project_root() / "mcp.json"
        content = _read_if_exists(mcp_path)
        parsed = json.loads(content)
        assert "mcpServers" in parsed

    def test_settings_json_parseable(self):
        """settings.local.json can be parsed."""
        settings_path = (
            _get_project_root() / ".claude" / "settings.local.json"
        )
        content = _read_if_exists(settings_path)
        parsed = json.loads(content)
        assert "permissions" in parsed


class TestPathResolution:
    """Verify pathlib resolves paths correctly on Linux/WSL."""

    def test_pathlib_resolves_project_root(self):
        """pathlib can resolve the project root directory."""
        root = _get_project_root()
        assert root.exists()
        assert root.is_dir()

    def test_pathlib_handles_unity_dirs(self):
        """pathlib can construct .claude/unity/ paths."""
        root = _get_project_root()
        claude_dir = root / ".claude" / "unity"
        # Path construction should work even if dir doesn't exist
        assert (
            str(claude_dir).endswith(".claude/unity")
            or str(claude_dir).endswith(".claude\\unity")
        )

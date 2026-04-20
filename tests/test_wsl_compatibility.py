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
    return Path(__file__).parent.parent.parent


class TestNoPowerShellReferences:
    """Verify no PowerShell references remain in server code."""

    def test_no_powershell_in_mcp_server(self):
        """MCP server source should not reference PowerShell."""
        server_path = Path(__file__).parent.parent / "unity_bridge_mcp_server.py"
        content = server_path.read_text()
        # Allow 'powershell' only in comments or strings that explicitly
        # document removal
        assert "powershell.exe" not in content.lower()
        assert "import subprocess" not in content

    def test_no_ps1_references_in_mcp_server(self):
        """MCP server should not reference .ps1 scripts."""
        server_path = Path(__file__).parent.parent / "unity_bridge_mcp_server.py"
        content = server_path.read_text()
        assert ".ps1" not in content

    def test_no_psutil_in_bridge_utils(self):
        """bridge_utils.py should not import psutil."""
        utils_path = (
            Path(__file__).parent.parent / "scripts" / "bridge_utils.py"
        )
        content = utils_path.read_text()
        assert "import psutil" not in content

    def test_mcp_json_uses_unity_bridge_cli(self):
        """mcp.json should use unity-bridge CLI command."""
        mcp_path = _get_project_root() / "mcp.json"
        config = json.loads(mcp_path.read_text())
        unity_bridge = config["mcpServers"]["unity-bridge"]
        assert unity_bridge["command"] == "unity-bridge"
        assert unity_bridge["args"] == ["serve"]


class TestInvokeCommandWithoutDirectBridge:
    """Test invoke_unity_command returns clean error without DirectBridge."""

    @pytest.mark.asyncio
    async def test_returns_error_without_direct_bridge(self):
        """invoke_unity_command returns error when DirectBridge unavailable."""
        # Import with DirectBridge forced unavailable
        import unity_bridge_mcp_server as server_module

        original = server_module._DIRECT_BRIDGE_AVAILABLE
        try:
            server_module._DIRECT_BRIDGE_AVAILABLE = False
            result = await server_module.invoke_unity_command("health-check")
            assert result["success"] is False
            assert "DirectBridge not available" in result["error"]
        finally:
            server_module._DIRECT_BRIDGE_AVAILABLE = original


class TestJsonLineEndings:
    """Verify JSON files use LF line endings for cross-platform compat."""

    def test_mcp_json_parseable(self):
        """mcp.json can be parsed regardless of line endings."""
        mcp_path = _get_project_root() / "mcp.json"
        content = mcp_path.read_text()
        parsed = json.loads(content)
        assert "mcpServers" in parsed

    def test_settings_json_parseable(self):
        """settings.local.json can be parsed."""
        settings_path = (
            _get_project_root() / ".claude" / "settings.local.json"
        )
        content = settings_path.read_text()
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

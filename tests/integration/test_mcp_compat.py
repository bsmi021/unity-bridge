"""Integration tests for MCP tool definition compatibility.

Ensures the MCP tool names and schemas remain stable across refactoring.
These tests import from the MCP server module and verify that all
expected tool definitions are present.

Marked with @pytest.mark.integration.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

# Ensure project root is importable
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Expected MCP tool names — these MUST NOT change for backward compat
# ---------------------------------------------------------------------------

EXPECTED_TOOL_NAMES = {
    "unity_run_tests",
    "unity_query_hierarchy",
    "unity_get_component_data",
    "unity_set_component_data",
    "unity_add_component",
    "unity_validate_prefab",
    "unity_scene_operation",
    "unity_prefab_operation",
    "unity_playmode_control",
    "unity_read_console",
    "unity_capture_screenshot",
    "unity_profiler_sample",
    "unity_material_operation",
    "unity_asset_operation",
    "unity_build_operation",
    "unity_animator_operation",
    "unity_bridge_config",
    "unity_clear_console",
    "unity_get_selection",
    "unity_refresh_assets",
    "unity_focus_object",
    "unity_health_check",
    "unity_compile",
    "unity_execute_menu_item",
    "unity_batch",
    "unity_help",
}

# ---------------------------------------------------------------------------
# Tool name -> bridge command type mapping (from unity_bridge_mcp_server.py)
# ---------------------------------------------------------------------------

EXPECTED_TOOL_MAP = {
    "unity_run_tests": "run-tests",
    "unity_query_hierarchy": "query-hierarchy",
    "unity_get_component_data": "get-component-data",
    "unity_set_component_data": "set-component-data",
    "unity_add_component": "add-component",
    "unity_validate_prefab": "validate-prefab",
    "unity_scene_operation": "scene-operation",
    "unity_prefab_operation": "prefab-operation",
    "unity_playmode_control": "playmode-control",
    "unity_read_console": "read-console",
    "unity_capture_screenshot": "capture-screenshot",
    "unity_profiler_sample": "profiler-sample",
    "unity_material_operation": "material-operation",
    "unity_asset_operation": "asset-operation",
    "unity_build_operation": "build-operation",
    "unity_animator_operation": "animator-operation",
    "unity_clear_console": "clear-console",
    "unity_get_selection": "get-selection",
    "unity_refresh_assets": "refresh-assets",
    "unity_focus_object": "focus-object",
    "unity_compile": "compile",
    "unity_execute_menu_item": "execute-menu-item",
}


# ---------------------------------------------------------------------------
# Helper: extract tool definitions from the MCP server source
# ---------------------------------------------------------------------------


def _get_mcp_server_source() -> str:
    """Read the MCP server source file."""
    server_path = _PROJECT_ROOT / "unity_bridge_mcp_server.py"
    if not server_path.exists():
        pytest.skip("unity_bridge_mcp_server.py not found")
    return server_path.read_text(encoding="utf-8")


def _extract_tool_names_from_source(source: str) -> set[str]:
    """Parse tool names from name= parameters in the MCP server."""
    import re
    return set(re.findall(r'name="(unity_\w+)"', source))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMCPToolNames:

    def test_all_expected_tools_defined(self) -> None:
        source = _get_mcp_server_source()
        actual_names = _extract_tool_names_from_source(source)
        missing = EXPECTED_TOOL_NAMES - actual_names
        assert not missing, f"Missing MCP tool definitions: {missing}"

    def test_minimum_tool_count(self) -> None:
        source = _get_mcp_server_source()
        actual_names = _extract_tool_names_from_source(source)
        assert len(actual_names) >= 22, (
            f"Expected 22+ MCP tools, found {len(actual_names)}"
        )

    def test_no_tool_name_changes(self) -> None:
        """Verify none of the original tool names have been renamed."""
        source = _get_mcp_server_source()
        actual_names = _extract_tool_names_from_source(source)
        for name in EXPECTED_TOOL_NAMES:
            assert name in actual_names, (
                f"Tool '{name}' appears to have been renamed or removed"
            )


class TestMCPToolMap:

    def test_tool_map_present(self) -> None:
        """The tool_map dict mapping tool names to bridge commands exists."""
        source = _get_mcp_server_source()
        assert "tool_map" in source

    def test_known_mappings_intact(self) -> None:
        """Verify known tool->command mappings haven't changed."""
        source = _get_mcp_server_source()
        for tool_name, cmd_type in EXPECTED_TOOL_MAP.items():
            # Check that the mapping string exists in source
            assert f'"{tool_name}": "{cmd_type}"' in source or \
                f"'{tool_name}': '{cmd_type}'" in source, (
                    f"Mapping {tool_name} -> {cmd_type} not found in source"
                )


class TestMCPToolSchemas:

    def test_tools_have_descriptions(self) -> None:
        """Each tool definition should include a description."""
        source = _get_mcp_server_source()
        # Each Tool() call should have a description parameter
        import re
        tool_blocks = re.findall(
            r'Tool\(\s*name="unity_\w+".*?\)', source, re.DOTALL
        )
        for block in tool_blocks:
            assert "description=" in block, (
                f"Tool block missing description: {block[:80]}..."
            )

    def test_tools_have_input_schemas(self) -> None:
        """Each tool should define its inputSchema."""
        source = _get_mcp_server_source()
        import re
        tool_blocks = re.findall(
            r'Tool\(\s*name="unity_\w+".*?\)', source, re.DOTALL
        )
        # Most tools should have inputSchema (a few like health_check may not)
        schemas_count = sum(1 for b in tool_blocks if "inputSchema" in b)
        assert schemas_count >= 15, (
            f"Expected 15+ tools with inputSchema, found {schemas_count}"
        )

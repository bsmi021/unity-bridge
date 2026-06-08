"""Unit tests for Phase 4 graph/editor-state surfaces."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.commands import graph_toolkit, scene_state


def _call_args(mock: MagicMock) -> dict[str, Any]:
    call = mock.send_command_with_retry.call_args
    return call.kwargs if call.kwargs else dict(
        zip(["command_type", "parameters", "timeout"], call.args, strict=False)
    )


class TestGraphToolkit:
    async def test_availability_dispatches(self, mock_bridge: MagicMock) -> None:
        await graph_toolkit.graph_toolkit_availability(mock_bridge)

        assert _call_args(mock_bridge)["command_type"] == "graph-toolkit"
        assert _call_args(mock_bridge)["parameters"] == {"operation": "availability"}

    async def test_export_dispatches_requested_options(self, mock_bridge: MagicMock) -> None:
        await graph_toolkit.graph_toolkit_export(
            mock_bridge,
            "Assets/Graphs/Combat.graph",
            include_ports=True,
            include_variables=True,
            max_elements=250,
        )

        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "export",
            "assetPath": "Assets/Graphs/Combat.graph",
            "includePorts": True,
            "includeVariables": True,
            "maxElements": 250,
        }


class TestSceneState:
    async def test_get_dispatches(self, mock_bridge: MagicMock) -> None:
        await scene_state.scene_state_get(mock_bridge)

        assert _call_args(mock_bridge)["command_type"] == "scene-state"
        assert _call_args(mock_bridge)["parameters"] == {"operation": "get"}

    async def test_set_dispatches_only_supplied_fields(self, mock_bridge: MagicMock) -> None:
        await scene_state.scene_state_set(
            mock_bridge,
            show_grid=False,
            grid_snap_enabled=True,
            grid_size=[1.0, 2.0, 3.0],
            active_tool="Move",
        )

        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "set",
            "showGrid": False,
            "gridSnapEnabled": True,
            "gridSize": [1.0, 2.0, 3.0],
            "activeTool": "Move",
        }


class TestGraphEditorStateRegistration:
    def test_tool_map_entries(self) -> None:
        from unity_bridge.mcp.tools import TOOL_COMMAND_MAP

        assert TOOL_COMMAND_MAP["unity_graph_toolkit"] == "graph-toolkit"
        assert TOOL_COMMAND_MAP["unity_scene_state"] == "scene-state"

    def test_timeout_defaults(self) -> None:
        from unity_bridge.core.protocol import PARALLEL_SAFE_COMMANDS, TIMEOUT_DEFAULTS

        assert TIMEOUT_DEFAULTS["graph-toolkit"] == 30
        assert TIMEOUT_DEFAULTS["scene-state"] == 10
        assert "graph-toolkit" in PARALLEL_SAFE_COMMANDS
        assert "scene-state" not in PARALLEL_SAFE_COMMANDS

    def test_schemas_include_expected_operations(self) -> None:
        from unity_bridge.mcp import schemas_editor_state

        graph_ops = schemas_editor_state.graph_toolkit()["properties"]["operation"]["enum"]
        state_ops = schemas_editor_state.scene_state()["properties"]["operation"]["enum"]
        assert "export" in graph_ops
        assert "reset-snap" in state_ops

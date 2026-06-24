"""Unit tests for the complete MCP tool definition surface."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from unity_bridge.core.health import HealthStatus
from unity_bridge.core.operation import OperationStore
from unity_bridge.mcp import schemas
from unity_bridge.mcp.server import (
    _handle_health_check,
    _handle_operation_status,
    _handle_submit_command,
)
from unity_bridge.core.protocol import TIMEOUT_DEFAULTS
from unity_bridge.mcp.tools import TOOL_COMMAND_MAP, TOOL_DEFINITIONS

CLIENT_SIDE_TOOLS = {
    "unity_bridge_config",
    "unity_health_check",
    "unity_operation_status",
    "unity_submit_command",
    "unity_batch",
    "unity_help",
}

SPECIAL_HANDLER_TOOLS = {
    "unity_create_primitive",
    "unity_gameobject_set_active",
}

SPECIAL_HANDLER_COMMANDS = {
    "gameobject-operation",
}

EXPECTED_TOOL_MAP = {
    "unity_navmesh": "navmesh-operation",
    "unity_animation_clip": "animation-clip",
    "unity_terrain": "terrain-operation",
    "unity_reflection_probe": "reflection-probe",
    "unity_occlusion_culling": "occlusion-culling",
    "unity_addressables": "addressables",
    "unity_tilemap": "tilemap-operation",
    "unity_clipboard": "clipboard",
    "unity_preset": "preset-operation",
    "unity_scene_template": "scene-template",
    "unity_script_info": "script-info",
    "unity_deep_serialize": "deep-serialize",
    "unity_window_management": "window-management",
    "unity_input_system": "input-system",
    "unity_time_settings": "time-settings",
    "unity_graphics_settings": "graphics-settings",
    "unity_environment_settings": "environment-settings",
    "unity_audio_settings": "audio-settings",
    "unity_component_copy": "component-copy",
    "unity_component_reset": "component-reset",
    "unity_scene_view": "scene-view",
    "unity_game_view": "game-view",
    "unity_profiler_control": "profiler-control",
    "unity_sync_solution": "sync-solution",
    "unity_cloud_services": "cloud-services",
    "unity_physics2d_config": "physics2d-config",
    "unity_search_query": "search-query",
    "unity_object_identity": "object-identity",
    "unity_project_auditor": "project-auditor",
    "unity_ui_toolkit": "ui-toolkit",
    "unity_render_pipeline": "render-pipeline",
    "unity_graphics_state": "graphics-state",
    "unity_graph_toolkit": "graph-toolkit",
    "unity_scene_state": "scene-state",
    "unity_entities": "entities",
    "unity_adaptive_performance": "adaptive-performance",
    "unity_multiplayer_playmode": "multiplayer-playmode",
}

EXPECTED_TOOL_GROUPS = {
    "Phase 4 extension": {
        "unity_navmesh",
        "unity_animation_clip",
        "unity_terrain",
        "unity_reflection_probe",
        "unity_occlusion_culling",
        "unity_addressables",
        "unity_tilemap",
    },
    "Phase 4 misc": {
        "unity_clipboard",
        "unity_preset",
        "unity_scene_template",
        "unity_script_info",
        "unity_deep_serialize",
        "unity_window_management",
        "unity_input_system",
    },
    "Phase 6 settings": {
        "unity_time_settings",
        "unity_graphics_settings",
        "unity_environment_settings",
        "unity_audio_settings",
    },
    "Phase 6b": {
        "unity_component_copy",
        "unity_component_reset",
        "unity_scene_view",
        "unity_game_view",
        "unity_profiler_control",
    },
    "Phase 7a": {
        "unity_sync_solution",
        "unity_cloud_services",
        "unity_physics2d_config",
        "unity_search_query",
    },
    "Unity 6.4": {
        "unity_object_identity",
        "unity_project_auditor",
        "unity_ui_toolkit",
        "unity_render_pipeline",
        "unity_graphics_state",
        "unity_graph_toolkit",
        "unity_scene_state",
        "unity_entities",
        "unity_adaptive_performance",
        "unity_multiplayer_playmode",
    },
}


def _tool_names() -> set[str]:
    return {tool["name"] for tool in TOOL_DEFINITIONS}


def test_tool_definitions_have_unique_names() -> None:
    names = [tool["name"] for tool in TOOL_DEFINITIONS]

    assert len(names) == len(set(names))


def test_every_tool_definition_is_mapped_or_explicitly_handled() -> None:
    mapped_or_handled = set(TOOL_COMMAND_MAP) | CLIENT_SIDE_TOOLS | SPECIAL_HANDLER_TOOLS

    assert _tool_names() - mapped_or_handled == set()


def test_expected_new_tool_mappings_are_registered() -> None:
    missing = {
        tool_name: command_type
        for tool_name, command_type in EXPECTED_TOOL_MAP.items()
        if TOOL_COMMAND_MAP.get(tool_name) != command_type
    }

    assert missing == {}


@pytest.mark.parametrize(("group_name", "expected_names"), EXPECTED_TOOL_GROUPS.items())
def test_phase_tool_groups_are_present(group_name: str, expected_names: set[str]) -> None:
    missing = expected_names - _tool_names()

    assert missing == set(), f"{group_name} tools missing: {sorted(missing)}"


def test_special_handler_tools_are_not_bridge_command_map_entries() -> None:
    assert SPECIAL_HANDLER_TOOLS <= _tool_names()
    assert SPECIAL_HANDLER_TOOLS.isdisjoint(TOOL_COMMAND_MAP)


def test_mapped_command_types_have_timeout_defaults() -> None:
    command_types = set(TOOL_COMMAND_MAP.values()) | SPECIAL_HANDLER_COMMANDS
    missing = command_types - set(TIMEOUT_DEFAULTS)

    assert missing == set()


def test_health_check_schema_exposes_wait_for_ready() -> None:
    schema = schemas.health_check()

    assert "waitForReady" in schema["properties"]
    assert "waitForHealthy" in schema["properties"]


async def test_health_check_wait_for_ready_uses_readiness_gate(tmp_path: Path) -> None:
    ready = HealthStatus(healthy=True, ready=True)

    with (
        patch("unity_bridge.mcp.server.HealthMonitor") as monitor_type,
        patch("unity_bridge.mcp.server.asyncio.to_thread", new_callable=AsyncMock) as wait,
    ):
        wait.return_value = ready
        result = await _handle_health_check({"waitForReady": True}, tmp_path)

    assert result["success"] is True
    assert result["health"]["ready"] is True
    wait.assert_awaited_once_with(
        monitor_type.return_value.wait_for_ready,
        timeout_seconds=30.0,
    )


async def test_health_check_wait_for_healthy_remains_liveness_only(tmp_path: Path) -> None:
    busy = HealthStatus(healthy=True, ready=False, is_compiling=True, busy_reason="compiling")

    with (
        patch("unity_bridge.mcp.server.HealthMonitor") as monitor_type,
        patch("unity_bridge.mcp.server.asyncio.to_thread", new_callable=AsyncMock) as wait,
    ):
        wait.return_value = busy
        result = await _handle_health_check({"waitForHealthy": True}, tmp_path)

    assert result["success"] is True
    assert result["health"]["healthy"] is True
    assert result["health"]["ready"] is False
    wait.assert_awaited_once_with(
        monitor_type.return_value.wait_for_healthy,
        timeout_seconds=30.0,
    )


async def test_operation_status_reads_persisted_operation(tmp_path: Path) -> None:
    store = OperationStore(tmp_path)
    store.create_queued(
        command_id="cmd-1",
        command_type="query-hierarchy",
        parameters={},
        command_path=tmp_path / "cmd.json",
        response_path=tmp_path / "resp.json",
        domain_generation=3,
        retry_policy="read_only",
    )

    result = await _handle_operation_status({"commandId": "cmd-1"}, tmp_path)

    assert result["success"] is True
    assert result["data"]["commandId"] == "cmd-1"
    assert result["data"]["domainGeneration"] == 3


def test_submit_command_tool_is_registered() -> None:
    assert "unity_submit_command" in _tool_names()


def test_submit_command_schema_requires_command_type() -> None:
    from unity_bridge.mcp import schemas_operations

    schema = schemas_operations.submit_command()

    assert schema["required"] == ["commandType"]
    assert "parameters" in schema["properties"]


async def test_submit_command_queues_without_unity_round_trip(tmp_path: Path) -> None:
    queued = {
        "success": True,
        "data": {"status": "queued", "commandId": "cmd-1"},
        "command_id": "cmd-1",
    }

    with patch("unity_bridge.mcp.server._get_command_queue") as get_queue:
        get_queue.return_value.submit.return_value.to_dict.return_value = queued
        result = await _handle_submit_command(
            {
                "commandType": "query-hierarchy",
                "parameters": {"maxDepth": 1},
                "timeout": 5,
            },
            tmp_path,
        )

    assert result == queued
    get_queue.return_value.submit.assert_called_once_with(
        "query-hierarchy",
        {"maxDepth": 1},
        5.0,
    )


async def test_submit_command_requires_command_type(tmp_path: Path) -> None:
    with patch("unity_bridge.mcp.server._get_command_queue") as get_queue:
        result = await _handle_submit_command({}, tmp_path)

    assert result == {"success": False, "error": "commandType is required", "exit_code": 3}
    get_queue.assert_not_called()


async def test_submit_command_ignores_non_object_parameters(tmp_path: Path) -> None:
    queued = {
        "success": True,
        "data": {"status": "queued", "commandId": "cmd-1"},
        "command_id": "cmd-1",
    }

    with patch("unity_bridge.mcp.server._get_command_queue") as get_queue:
        get_queue.return_value.submit.return_value.to_dict.return_value = queued
        result = await _handle_submit_command(
            {
                "commandType": "query-hierarchy",
                "parameters": ["not", "an", "object"],
                "timeout": 5,
            },
            tmp_path,
        )

    assert result is queued
    get_queue.return_value.submit.assert_called_once_with("query-hierarchy", {}, 5.0)

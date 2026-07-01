"""Unit tests for Phase 7a (Query & Report) command modules."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from unity_bridge.commands import cloud_services, physics2d, search, sync_solution


def _call_args(mock: MagicMock) -> dict[str, Any]:
    call = mock.send_command_with_retry.call_args
    return call.kwargs if call.kwargs else dict(zip(
        ["command_type", "parameters", "timeout"], call.args, strict=False
    ))


# ---------------------------------------------------------------------------
# sync_solution
# ---------------------------------------------------------------------------


class TestSyncSolution:
    async def test_command_type(self, mock_bridge: MagicMock) -> None:
        await sync_solution.sync_solution(mock_bridge)
        assert _call_args(mock_bridge)["command_type"] == "sync-solution"

    async def test_empty_parameters(self, mock_bridge: MagicMock) -> None:
        await sync_solution.sync_solution(mock_bridge)
        assert _call_args(mock_bridge)["parameters"] == {}


# ---------------------------------------------------------------------------
# cloud_services
# ---------------------------------------------------------------------------


class TestCloudServices:
    @pytest.mark.parametrize(
        ("func", "op"),
        [
            (cloud_services.get_project_id, "get-project-id"),
            (cloud_services.get_environments, "get-environments"),
            (cloud_services.get_active_environment, "get-active-environment"),
        ],
    )
    async def test_operation_dispatch(
        self, mock_bridge: MagicMock, func: Any, op: str
    ) -> None:
        await func(mock_bridge)
        args = _call_args(mock_bridge)
        assert args["command_type"] == "cloud-services"
        assert args["parameters"] == {"operation": op}


# ---------------------------------------------------------------------------
# physics2d
# ---------------------------------------------------------------------------


class TestPhysics2D:
    async def test_get_dispatches(self, mock_bridge: MagicMock) -> None:
        await physics2d.physics2d_get(mock_bridge)
        args = _call_args(mock_bridge)
        assert args["command_type"] == "physics2d-config"
        assert args["parameters"] == {"operation": "get"}

    async def test_set_gravity_only_sends_gravity_flags(
        self, mock_bridge: MagicMock
    ) -> None:
        await physics2d.physics2d_set(mock_bridge, gravity=(0.0, -9.81))
        params = _call_args(mock_bridge)["parameters"]
        assert params["operation"] == "set"
        assert params["setGravity"] is True
        assert params["gravityX"] == 0.0
        assert params["gravityY"] == -9.81
        assert "setVelocityIterations" not in params

    async def test_set_multiple_fields(self, mock_bridge: MagicMock) -> None:
        await physics2d.physics2d_set(
            mock_bridge,
            velocity_iterations=10,
            queries_hit_triggers=True,
        )
        params = _call_args(mock_bridge)["parameters"]
        assert params["setVelocityIterations"] is True
        assert params["velocityIterations"] == 10
        assert params["setQueriesHitTriggers"] is True
        assert params["queriesHitTriggers"] is True

    async def test_matrix_dispatches(self, mock_bridge: MagicMock) -> None:
        await physics2d.physics2d_get_matrix(mock_bridge)
        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "get-collision-matrix"
        }

    async def test_set_collision(self, mock_bridge: MagicMock) -> None:
        await physics2d.physics2d_set_collision(mock_bridge, 8, 9, False)
        params = _call_args(mock_bridge)["parameters"]
        assert params == {
            "operation": "set-collision",
            "layerA": 8,
            "layerB": 9,
            "collides": False,
        }


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


class TestSearch:
    async def test_query_dispatches(self, mock_bridge: MagicMock) -> None:
        await search.search_query(mock_bridge, "t:Material", max_results=50)
        args = _call_args(mock_bridge)
        assert args["command_type"] == "search-query"
        assert args["parameters"] == {
            "operation": "query",
            "query": "t:Material",
            "maxResults": 50,
        }

    async def test_providers_dispatches(self, mock_bridge: MagicMock) -> None:
        await search.search_providers(mock_bridge)
        args = _call_args(mock_bridge)
        assert args["parameters"] == {"operation": "providers"}


# ---------------------------------------------------------------------------
# Protocol registration
# ---------------------------------------------------------------------------


class TestProtocolRegistration:
    def test_timeouts_declared(self) -> None:
        from unity_bridge.core.protocol import TIMEOUT_DEFAULTS

        for cmd in (
            "sync-solution",
            "cloud-services",
            "physics2d-config",
            "search-query",
        ):
            assert cmd in TIMEOUT_DEFAULTS, f"{cmd} missing timeout default"

    def test_read_only_ops_are_parallel_safe(self) -> None:
        from unity_bridge.core.protocol import PARALLEL_SAFE_COMMANDS

        assert "cloud-services" in PARALLEL_SAFE_COMMANDS
        assert "search-query" in PARALLEL_SAFE_COMMANDS

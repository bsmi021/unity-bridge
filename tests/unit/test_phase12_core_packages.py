"""Unit tests for Phase 5 Unity built-in package surfaces."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.commands import adaptive_performance, entities


def _call_args(mock: MagicMock) -> dict[str, Any]:
    call = mock.send_command_with_retry.call_args
    return call.kwargs if call.kwargs else dict(
        zip(["command_type", "parameters", "timeout"], call.args, strict=False)
    )


class TestEntities:
    async def test_availability_dispatches(self, mock_bridge: MagicMock) -> None:
        await entities.entities_availability(mock_bridge)

        assert _call_args(mock_bridge)["command_type"] == "entities"
        assert _call_args(mock_bridge)["parameters"] == {"operation": "availability"}

    async def test_list_systems_dispatches_requested_options(
        self, mock_bridge: MagicMock
    ) -> None:
        await entities.entities_list_systems(
            mock_bridge,
            world_name="Default World",
            namespace_filter="Unity.Transforms",
            max_systems=25,
        )

        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "list-systems",
            "worldName": "Default World",
            "namespaceFilter": "Unity.Transforms",
            "maxSystems": 25,
        }

    async def test_list_archetypes_dispatches_requested_options(
        self, mock_bridge: MagicMock
    ) -> None:
        await entities.entities_list_archetypes(
            mock_bridge,
            world_name="Default World",
            include_components=True,
            max_archetypes=10,
            max_components=16,
        )

        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "list-archetypes",
            "worldName": "Default World",
            "includeComponents": True,
            "maxArchetypes": 10,
            "maxComponents": 16,
        }


class TestAdaptivePerformance:
    async def test_settings_dispatches(self, mock_bridge: MagicMock) -> None:
        await adaptive_performance.adaptive_performance_settings(mock_bridge)

        assert _call_args(mock_bridge)["command_type"] == "adaptive-performance"
        assert _call_args(mock_bridge)["parameters"] == {"operation": "settings"}

    async def test_inspect_profile_dispatches_asset_path(self, mock_bridge: MagicMock) -> None:
        await adaptive_performance.adaptive_performance_inspect_profile(
            mock_bridge,
            "Assets/Adaptive/Default.asset",
            include_scalers=True,
        )

        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "inspect-profile",
            "assetPath": "Assets/Adaptive/Default.asset",
            "includeScalers": True,
        }


class TestCorePackageRegistration:
    def test_timeout_defaults(self) -> None:
        from unity_bridge.core.protocol import PARALLEL_SAFE_COMMANDS, TIMEOUT_DEFAULTS

        assert TIMEOUT_DEFAULTS["entities"] == 15
        assert TIMEOUT_DEFAULTS["adaptive-performance"] == 15
        assert "entities" in PARALLEL_SAFE_COMMANDS
        assert "adaptive-performance" in PARALLEL_SAFE_COMMANDS

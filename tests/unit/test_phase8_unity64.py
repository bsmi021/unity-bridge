"""Unit tests for Unity 6.4 opportunity command surfaces."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.commands import object_identity, project_auditor


def _call_args(mock: MagicMock) -> dict[str, Any]:
    call = mock.send_command_with_retry.call_args
    return call.kwargs if call.kwargs else dict(
        zip(["command_type", "parameters", "timeout"], call.args, strict=False)
    )


class TestObjectIdentity:
    async def test_get_selection_dispatches(self, mock_bridge: MagicMock) -> None:
        await object_identity.get_selection_identities(mock_bridge)

        args = _call_args(mock_bridge)
        assert args["command_type"] == "object-identity"
        assert args["parameters"] == {"operation": "get-selection"}

    async def test_resolve_sends_only_provided_target(
        self, mock_bridge: MagicMock
    ) -> None:
        await object_identity.resolve_identity(
            mock_bridge,
            asset_path="Assets/Player.prefab",
            global_object_id="GlobalObjectId_V1-1-abc-1-0",
        )

        args = _call_args(mock_bridge)
        assert args["command_type"] == "object-identity"
        assert args["parameters"] == {
            "operation": "resolve",
            "assetPath": "Assets/Player.prefab",
            "globalObjectId": "GlobalObjectId_V1-1-abc-1-0",
        }

    async def test_ping_dispatches(self, mock_bridge: MagicMock) -> None:
        await object_identity.ping_identity(mock_bridge, instance_id=123)

        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "ping",
            "instanceId": 123,
        }

    async def test_resolve_entity_id_dispatches(self, mock_bridge: MagicMock) -> None:
        await object_identity.resolve_identity(mock_bridge, entity_id="123")

        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "resolve",
            "entityId": "123",
        }


class TestProjectAuditor:
    async def test_availability_dispatches(self, mock_bridge: MagicMock) -> None:
        await project_auditor.project_auditor_availability(mock_bridge)

        args = _call_args(mock_bridge)
        assert args["command_type"] == "project-auditor"
        assert args["parameters"] == {"operation": "availability"}

    async def test_run_dispatches_filters(self, mock_bridge: MagicMock) -> None:
        await project_auditor.project_auditor_run(
            mock_bridge,
            output_path="Temp/project-auditor.json",
            max_issues=25,
            categories=["Code", "Assets"],
            assembly_names=["Game.Editor"],
            platform="StandaloneWindows64",
        )

        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "run",
            "outputPath": "Temp/project-auditor.json",
            "maxIssues": 25,
            "categories": ["Code", "Assets"],
            "assemblyNames": ["Game.Editor"],
            "platform": "StandaloneWindows64",
        }

    async def test_load_dispatches(self, mock_bridge: MagicMock) -> None:
        await project_auditor.project_auditor_load(
            mock_bridge,
            "Temp/project-auditor.json",
            max_issues=10,
        )

        assert _call_args(mock_bridge)["parameters"] == {
            "operation": "load",
            "outputPath": "Temp/project-auditor.json",
            "maxIssues": 10,
        }


class TestUnity64ProtocolRegistration:
    def test_timeouts_declared(self) -> None:
        from unity_bridge.core.protocol import TIMEOUT_DEFAULTS

        assert TIMEOUT_DEFAULTS["object-identity"] == 10
        assert TIMEOUT_DEFAULTS["project-auditor"] == 300

    def test_read_only_object_identity_is_parallel_safe(self) -> None:
        from unity_bridge.core.protocol import PARALLEL_SAFE_COMMANDS

        assert "object-identity" in PARALLEL_SAFE_COMMANDS

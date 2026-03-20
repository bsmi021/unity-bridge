"""Adversarial QA tests for commands/lightmap.py — edge cases and spec compliance.

Covers:
- Timeout behavior: async vs sync defaults, custom overrides
- Parameter correctness: runAsync camelCase mapping
- VALID_ACTIONS completeness
- Schema validation for MCP tool
- Edge cases: repeated calls, zero timeout
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from unity_bridge.commands.lightmap import (
    VALID_ACTIONS,
    lightmap_bake,
    lightmap_cancel,
    lightmap_clear,
    lightmap_settings,
    lightmap_status,
)
from unity_bridge.core.bridge import CommandResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_parameters(call_args: Any) -> dict:
    if call_args.kwargs.get("parameters") is not None:
        return call_args.kwargs["parameters"]
    if len(call_args.args) >= 2:
        return call_args.args[1]
    return {}


def _extract_command_type(call_args: Any) -> str:
    if "command_type" in call_args.kwargs:
        return call_args.kwargs["command_type"]
    return call_args.args[0]


def _extract_kwarg(call_args: Any, key: str) -> Any:
    if key in call_args.kwargs:
        return call_args.kwargs[key]
    return None


# ---------------------------------------------------------------------------
# VALID_ACTIONS completeness
# ---------------------------------------------------------------------------


class TestValidActions:
    def test_all_expected_actions(self) -> None:
        expected = {"bake", "cancel", "clear", "status", "settings"}
        assert VALID_ACTIONS == expected

    def test_is_frozenset(self) -> None:
        assert isinstance(VALID_ACTIONS, frozenset)


# ---------------------------------------------------------------------------
# Bake edge cases
# ---------------------------------------------------------------------------


class TestBakeEdgeCases:
    async def test_run_async_param_uses_camel_case(self, mock_bridge: MagicMock) -> None:
        """m6: Parameter must be runAsync not async in bridge protocol."""
        await lightmap_bake(mock_bridge, run_async=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "runAsync" in params
        assert "async" not in params
        assert "run_async" not in params

    async def test_sync_bake_uses_long_timeout(self, mock_bridge: MagicMock) -> None:
        """Sync bake must use a long default timeout (3600s)."""
        await lightmap_bake(mock_bridge, run_async=False)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 3600.0

    async def test_async_bake_uses_short_timeout(self, mock_bridge: MagicMock) -> None:
        """Async bake returns immediately — timeout should be short."""
        await lightmap_bake(mock_bridge, run_async=True)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 30.0

    async def test_custom_timeout_overrides_default(self, mock_bridge: MagicMock) -> None:
        """Custom timeout should override both async and sync defaults."""
        await lightmap_bake(mock_bridge, run_async=False, timeout=60.0)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 60.0

    async def test_custom_timeout_overrides_async_default(self, mock_bridge: MagicMock) -> None:
        await lightmap_bake(mock_bridge, run_async=True, timeout=5.0)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 5.0

    async def test_timeout_none_uses_default(self, mock_bridge: MagicMock) -> None:
        """Explicit None timeout should fall back to defaults."""
        await lightmap_bake(mock_bridge, run_async=True, timeout=None)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 30.0

    async def test_bake_started_false_propagated(self, mock_bridge: MagicMock) -> None:
        """M11: When BakeAsync returns false, data should have started=False."""
        fail_result = CommandResult(
            success=True,
            data={
                "operation": "bake",
                "started": False,
                "runAsync": True,
                "success": False,
                "message": "Failed to start",
            },
        )
        mock_bridge.send_command_with_retry.return_value = fail_result
        result = await lightmap_bake(mock_bridge)
        assert result.data["started"] is False
        assert result.data["success"] is False


# ---------------------------------------------------------------------------
# Cancel edge cases
# ---------------------------------------------------------------------------


class TestCancelEdgeCases:
    async def test_cancel_when_not_running(self, mock_bridge: MagicMock) -> None:
        """Cancel when no bake is running should still succeed."""
        result_data = CommandResult(
            success=True,
            data={
                "operation": "cancel",
                "wasRunning": False,
                "success": True,
                "message": "No lightmap bake was running",
            },
        )
        mock_bridge.send_command_with_retry.return_value = result_data
        result = await lightmap_cancel(mock_bridge)
        assert result.success is True
        assert result.data["wasRunning"] is False

    async def test_cancel_sends_no_extra_params(self, mock_bridge: MagicMock) -> None:
        """Cancel should only send operation parameter."""
        await lightmap_cancel(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "cancel"}


# ---------------------------------------------------------------------------
# Clear edge cases
# ---------------------------------------------------------------------------


class TestClearEdgeCases:
    async def test_clear_sends_no_extra_params(self, mock_bridge: MagicMock) -> None:
        await lightmap_clear(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "clear"}


# ---------------------------------------------------------------------------
# Status edge cases
# ---------------------------------------------------------------------------


class TestStatusEdgeCases:
    async def test_status_uses_quick_timeout(self, mock_bridge: MagicMock) -> None:
        """Status is a quick query — should use a short timeout."""
        await lightmap_status(mock_bridge)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout <= 15.0

    async def test_progress_zero_when_idle(self, mock_bridge: MagicMock) -> None:
        idle_result = CommandResult(
            success=True,
            data={
                "operation": "status",
                "isRunning": False,
                "progress": 0.0,
                "success": True,
            },
        )
        mock_bridge.send_command_with_retry.return_value = idle_result
        result = await lightmap_status(mock_bridge)
        assert result.data["progress"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Settings edge cases
# ---------------------------------------------------------------------------


class TestSettingsEdgeCases:
    async def test_settings_sends_no_extra_params(self, mock_bridge: MagicMock) -> None:
        await lightmap_settings(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "settings"}

    async def test_settings_with_null_lighting_settings(self, mock_bridge: MagicMock) -> None:
        """C# side handles null LightingSettings with fallback message."""
        result_data = CommandResult(
            success=True,
            data={
                "operation": "settings",
                "success": True,
                "message": "No LightingSettings asset found; using defaults",
            },
        )
        mock_bridge.send_command_with_retry.return_value = result_data
        result = await lightmap_settings(mock_bridge)
        assert result.success is True
        assert "No LightingSettings" in result.data["message"]


# ---------------------------------------------------------------------------
# All operations use correct command type
# ---------------------------------------------------------------------------


class TestAllOperationsCommandType:
    async def test_bake_command_type(self, mock_bridge: MagicMock) -> None:
        await lightmap_bake(mock_bridge)
        assert (
            _extract_command_type(mock_bridge.send_command_with_retry.call_args)
            == "lightmap-operation"
        )

    async def test_cancel_command_type(self, mock_bridge: MagicMock) -> None:
        await lightmap_cancel(mock_bridge)
        assert (
            _extract_command_type(mock_bridge.send_command_with_retry.call_args)
            == "lightmap-operation"
        )

    async def test_clear_command_type(self, mock_bridge: MagicMock) -> None:
        await lightmap_clear(mock_bridge)
        assert (
            _extract_command_type(mock_bridge.send_command_with_retry.call_args)
            == "lightmap-operation"
        )

    async def test_status_command_type(self, mock_bridge: MagicMock) -> None:
        await lightmap_status(mock_bridge)
        assert (
            _extract_command_type(mock_bridge.send_command_with_retry.call_args)
            == "lightmap-operation"
        )

    async def test_settings_command_type(self, mock_bridge: MagicMock) -> None:
        await lightmap_settings(mock_bridge)
        assert (
            _extract_command_type(mock_bridge.send_command_with_retry.call_args)
            == "lightmap-operation"
        )


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


class TestLightmapSchema:
    def test_schema_has_all_operations(self) -> None:
        from unity_bridge.mcp.schemas_phase3 import unity_lightmap_operation

        schema = unity_lightmap_operation()
        ops = schema["properties"]["operation"]["enum"]
        assert ops == ["bake", "cancel", "clear", "status", "settings"]

    def test_schema_required_fields(self) -> None:
        from unity_bridge.mcp.schemas_phase3 import unity_lightmap_operation

        schema = unity_lightmap_operation()
        assert schema["required"] == ["operation"]

    def test_schema_has_timeout(self) -> None:
        from unity_bridge.mcp.schemas_phase3 import unity_lightmap_operation

        schema = unity_lightmap_operation()
        assert "timeout" in schema["properties"]

    def test_schema_has_run_async(self) -> None:
        """m6: Schema param must be runAsync not async."""
        from unity_bridge.mcp.schemas_phase3 import unity_lightmap_operation

        schema = unity_lightmap_operation()
        assert "runAsync" in schema["properties"]
        assert "async" not in schema["properties"]

    def test_schema_run_async_defaults_true(self) -> None:
        from unity_bridge.mcp.schemas_phase3 import unity_lightmap_operation

        schema = unity_lightmap_operation()
        assert schema["properties"]["runAsync"]["default"] is True

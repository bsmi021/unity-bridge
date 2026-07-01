"""Unit tests for commands/vfx.py — VisualEffectAsset inspection (read-only)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from typer.testing import CliRunner

from unity_bridge.commands.vfx import vfx_app, vfx_get_info
from unity_bridge.core.output import OutputFormatter

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


def _state(mock_bridge: MagicMock) -> SimpleNamespace:
    return SimpleNamespace(bridge=mock_bridge, formatter=OutputFormatter())


def _run_vfx(args: list[str], mock_bridge: MagicMock):
    runner = CliRunner()
    return runner.invoke(vfx_app, args, obj=_state(mock_bridge))


# ---------------------------------------------------------------------------
# vfx_get_info — core async function
# ---------------------------------------------------------------------------


class TestVfxGetInfo:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await vfx_get_info(mock_bridge, asset_path="Assets/Fx/Explosion.vfx")
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "vfx-asset"

    async def test_asset_path_only_omits_guid(self, mock_bridge: MagicMock) -> None:
        await vfx_get_info(mock_bridge, asset_path="Assets/Fx/Explosion.vfx")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "get-info", "assetPath": "Assets/Fx/Explosion.vfx"}
        assert "guid" not in params

    async def test_guid_only_omits_asset_path(self, mock_bridge: MagicMock) -> None:
        await vfx_get_info(mock_bridge, guid="abc123def456")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "get-info", "guid": "abc123def456"}
        assert "assetPath" not in params

    async def test_neither_arg_sends_bare_operation(self, mock_bridge: MagicMock) -> None:
        await vfx_get_info(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "get-info"}

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        await vfx_get_info(mock_bridge, asset_path="Assets/Fx/Explosion.vfx")
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 15.0

    async def test_custom_timeout_propagates(self, mock_bridge: MagicMock) -> None:
        await vfx_get_info(mock_bridge, asset_path="Assets/Fx/Explosion.vfx", timeout=5.0)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 5.0

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await vfx_get_info(failing_bridge, asset_path="Assets/Fx/Explosion.vfx")
        assert result.success is False

    async def test_returns_command_result_with_event_and_property_lists(
        self, mock_bridge: MagicMock
    ) -> None:
        from unity_bridge.core.bridge import CommandResult

        expected = CommandResult(
            success=True,
            data={
                "operation": "get-info",
                "assetPath": "Assets/Fx/Explosion.vfx",
                "eventNames": ["OnPlay", "OnStop"],
                "exposedProperties": [{"name": "Size", "type": "Single"}],
                "success": True,
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await vfx_get_info(mock_bridge, asset_path="Assets/Fx/Explosion.vfx")
        assert result.data["eventNames"] == ["OnPlay", "OnStop"]
        assert result.data["exposedProperties"] == [{"name": "Size", "type": "Single"}]

    async def test_uses_send_command_with_retry_not_send_command(
        self, mock_bridge: MagicMock
    ) -> None:
        await vfx_get_info(mock_bridge, asset_path="Assets/Fx/Explosion.vfx")
        assert mock_bridge.send_command_with_retry.call_count == 1
        assert mock_bridge.send_command.call_count == 0


# ---------------------------------------------------------------------------
# CLI wrapper
# ---------------------------------------------------------------------------


class TestVfxGetInfoCli:
    """Typer collapses a single-command sub-app: invoke without the
    subcommand name (mirrors the same Typer behavior exercised, though not
    accounted for, by test_commands_memory_profiler.py's analogous CLI
    tests for the also-single-command memory_profiler_app).
    """

    def test_get_info_cli_sends_asset_path(self, mock_bridge: MagicMock) -> None:
        result = _run_vfx(["--asset-path", "Assets/Fx/Explosion.vfx"], mock_bridge)

        assert result.exit_code == 0
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "get-info", "assetPath": "Assets/Fx/Explosion.vfx"}

    def test_get_info_cli_sends_guid(self, mock_bridge: MagicMock) -> None:
        result = _run_vfx(["--guid", "abc123def456"], mock_bridge)

        assert result.exit_code == 0
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params == {"operation": "get-info", "guid": "abc123def456"}

    def test_get_info_cli_failure_path(self, failing_bridge: MagicMock) -> None:
        result = _run_vfx(["--asset-path", "Assets/Fx/Explosion.vfx"], failing_bridge)

        assert result.exit_code != 0

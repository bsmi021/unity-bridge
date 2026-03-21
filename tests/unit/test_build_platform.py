"""Unit tests for build platform switching and extended build options."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.core.bridge import CommandResult


def _import_build():
    from unity_bridge.commands import build

    return build


# ---------------------------------------------------------------------------
# switch_platform
# ---------------------------------------------------------------------------


class TestSwitchPlatform:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_build()
        await mod.switch_platform(mock_bridge, "Android")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "build-operation"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_build()
        await mod.switch_platform(mock_bridge, "Android")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "switch-platform"
        assert params["target"] == "Android"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_build()
        await mod.switch_platform(mock_bridge, "WebGL")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 120.0

    async def test_custom_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_build()
        await mod.switch_platform(mock_bridge, "iOS", timeout=300.0)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 300.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_build()
        expected = CommandResult(
            success=True,
            data={"operation": "switch-platform", "buildTarget": "Android"},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.switch_platform(mock_bridge, "Android")
        assert result.success is True
        assert result.data["operation"] == "switch-platform"


# ---------------------------------------------------------------------------
# list_platforms
# ---------------------------------------------------------------------------


class TestListPlatforms:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_build()
        await mod.list_platforms(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "build-operation"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_build()
        await mod.list_platforms(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "list-platforms"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_build()
        await mod.list_platforms(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 15.0

    async def test_returns_platform_list(self, mock_bridge: MagicMock) -> None:
        mod = _import_build()
        expected = CommandResult(
            success=True,
            data={
                "operation": "list-platforms",
                "activePlatform": "StandaloneWindows64",
                "platforms": [
                    {"name": "Android", "isSupported": True, "isActive": False},
                ],
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.list_platforms(mock_bridge)
        assert result.success is True
        assert result.data["activePlatform"] == "StandaloneWindows64"


# ---------------------------------------------------------------------------
# build with extended options
# ---------------------------------------------------------------------------


class TestBuildExtendedOptions:
    async def test_auto_run_flag(self, mock_bridge: MagicMock) -> None:
        mod = _import_build()
        await mod.build(mock_bridge, "Android", auto_run=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["autoRunPlayer"] is True

    async def test_profiler_flag(self, mock_bridge: MagicMock) -> None:
        mod = _import_build()
        await mod.build(mock_bridge, "Android", profiler=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["connectProfiler"] is True

    async def test_compress_lz4hc(self, mock_bridge: MagicMock) -> None:
        mod = _import_build()
        await mod.build(mock_bridge, "Android", compress="lz4hc")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["compress"] == "lz4hc"

    async def test_custom_scenes(self, mock_bridge: MagicMock) -> None:
        mod = _import_build()
        scenes = ["Assets/Scenes/Main.unity", "Assets/Scenes/Game.unity"]
        await mod.build(mock_bridge, "Android", scenes=scenes)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["scenes"] == scenes

    async def test_subtarget(self, mock_bridge: MagicMock) -> None:
        mod = _import_build()
        await mod.build(mock_bridge, "StandaloneWindows64", subtarget="Server")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["subtarget"] == "Server"

    async def test_clean_build(self, mock_bridge: MagicMock) -> None:
        mod = _import_build()
        await mod.build(mock_bridge, "Android", clean=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["cleanBuildCache"] is True

    async def test_scripts_only(self, mock_bridge: MagicMock) -> None:
        mod = _import_build()
        await mod.build(mock_bridge, "Android", scripts_only=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["buildScriptsOnly"] is True

    async def test_validate_only_sets_operation(self, mock_bridge: MagicMock) -> None:
        mod = _import_build()
        await mod.build(mock_bridge, "Android", validate_only=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "validate"

    async def test_default_operation_is_build(self, mock_bridge: MagicMock) -> None:
        mod = _import_build()
        await mod.build(mock_bridge, "Android")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "build"

    async def test_flags_not_set_when_false(self, mock_bridge: MagicMock) -> None:
        mod = _import_build()
        await mod.build(mock_bridge, "Android")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "autoRunPlayer" not in params
        assert "connectProfiler" not in params
        assert "compress" not in params
        assert "scenes" not in params
        assert "subtarget" not in params


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

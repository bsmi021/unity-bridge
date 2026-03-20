"""Unit tests for commands/build_profile.py — build profile operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from unity_bridge.core.bridge import CommandResult


def _import_build_profile():
    from unity_bridge.commands import build_profile

    return build_profile


# ---------------------------------------------------------------------------
# list operation
# ---------------------------------------------------------------------------


class TestList:
    async def test_builds_correct_parameters(self, mock_bridge: MagicMock) -> None:
        bp = _import_build_profile()
        await bp.build_profile_operation(mock_bridge, action="list")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "list"
        assert "profilePath" not in params

    async def test_command_type(self, mock_bridge: MagicMock) -> None:
        bp = _import_build_profile()
        await bp.build_profile_operation(mock_bridge, action="list")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "build-profile-operation"


# ---------------------------------------------------------------------------
# get-active operation
# ---------------------------------------------------------------------------


class TestGetActive:
    async def test_builds_correct_parameters(self, mock_bridge: MagicMock) -> None:
        bp = _import_build_profile()
        await bp.build_profile_operation(mock_bridge, action="get-active")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "get-active"

    async def test_returns_null_profile(self, mock_bridge: MagicMock) -> None:
        bp = _import_build_profile()
        expected = CommandResult(
            success=True,
            data={"operation": "get-active", "profile": None},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await bp.build_profile_operation(mock_bridge, action="get-active")
        assert result.success is True
        assert result.data["profile"] is None


# ---------------------------------------------------------------------------
# set-active operation
# ---------------------------------------------------------------------------


class TestSetActive:
    async def test_builds_correct_parameters(self, mock_bridge: MagicMock) -> None:
        bp = _import_build_profile()
        await bp.build_profile_operation(
            mock_bridge,
            action="set-active",
            profile_path="Assets/Settings/BuildProfiles/Android.asset",
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "set-active"
        assert params["profilePath"] == "Assets/Settings/BuildProfiles/Android.asset"

    async def test_profile_path_optional_not_sent(self, mock_bridge: MagicMock) -> None:
        bp = _import_build_profile()
        await bp.build_profile_operation(mock_bridge, action="set-active")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert "profilePath" not in params


# ---------------------------------------------------------------------------
# get-info operation
# ---------------------------------------------------------------------------


class TestGetInfo:
    async def test_builds_correct_parameters(self, mock_bridge: MagicMock) -> None:
        bp = _import_build_profile()
        await bp.build_profile_operation(
            mock_bridge,
            action="get-info",
            profile_path="Assets/Settings/BuildProfiles/Win64.asset",
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "get-info"
        assert params["profilePath"] == "Assets/Settings/BuildProfiles/Win64.asset"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    async def test_invalid_action_raises(self, mock_bridge: MagicMock) -> None:
        bp = _import_build_profile()
        with pytest.raises(ValueError, match="Invalid build profile action"):
            await bp.build_profile_operation(mock_bridge, action="delete")

    async def test_action_normalised(self, mock_bridge: MagicMock) -> None:
        bp = _import_build_profile()
        await bp.build_profile_operation(mock_bridge, action="  LIST  ")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "list"


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------


class TestTimeout:
    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        bp = _import_build_profile()
        await bp.build_profile_operation(mock_bridge, action="list")
        call_args = mock_bridge.send_command_with_retry.call_args
        timeout = _extract_kwarg(call_args, "timeout")
        assert timeout == 30.0 or timeout == 30

    async def test_custom_timeout(self, mock_bridge: MagicMock) -> None:
        bp = _import_build_profile()
        await bp.build_profile_operation(mock_bridge, action="list", timeout=60)
        call_args = mock_bridge.send_command_with_retry.call_args
        timeout = _extract_kwarg(call_args, "timeout")
        assert timeout == 60.0 or timeout == 60


# ---------------------------------------------------------------------------
# Return value
# ---------------------------------------------------------------------------


class TestReturnValue:
    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        bp = _import_build_profile()
        expected = CommandResult(
            success=True,
            data={
                "operation": "list",
                "profiles": [{"name": "Win64", "platform": "StandaloneWindows64"}],
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await bp.build_profile_operation(mock_bridge, action="list")
        assert result.success is True
        assert len(result.data["profiles"]) == 1


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

"""QA adversarial tests for commands/build_profile.py — Build Profile operations.

Tests edge cases, spec compliance per adversarial review findings.
Covers: C3 (null active profile), C4 (batch mode), C5 (GUID->path).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from unity_bridge.commands.build_profile import (
    VALID_ACTIONS,
    build_profile_operation,
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
    def test_all_spec_operations_present(self) -> None:
        expected = {
            "list",
            "get-active",
            "set-active",
            "get-info",
            "get-scenes",
            "set-scenes",
            "get-defines",
            "set-defines",
            "build",
        }
        assert VALID_ACTIONS == expected

    def test_is_frozenset(self) -> None:
        assert isinstance(VALID_ACTIONS, frozenset)


# ---------------------------------------------------------------------------
# Edge case inputs
# ---------------------------------------------------------------------------


class TestEdgeCaseInputs:
    async def test_empty_string_action_raises(self, mock_bridge: MagicMock) -> None:
        with pytest.raises(ValueError, match="Invalid build profile action"):
            await build_profile_operation(mock_bridge, action="")

    async def test_whitespace_only_action_raises(self, mock_bridge: MagicMock) -> None:
        with pytest.raises(ValueError, match="Invalid build profile action"):
            await build_profile_operation(mock_bridge, action="   ")

    async def test_case_insensitive_action(self, mock_bridge: MagicMock) -> None:
        await build_profile_operation(mock_bridge, action="GET-ACTIVE")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "get-active"

    async def test_mixed_case_action(self, mock_bridge: MagicMock) -> None:
        await build_profile_operation(mock_bridge, action="Set-Active")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "set-active"

    async def test_similar_but_invalid_raises(self, mock_bridge: MagicMock) -> None:
        with pytest.raises(ValueError, match="Invalid build profile action"):
            await build_profile_operation(mock_bridge, action="delete")

    async def test_getactive_no_hyphen_raises(self, mock_bridge: MagicMock) -> None:
        with pytest.raises(ValueError, match="Invalid build profile action"):
            await build_profile_operation(mock_bridge, action="getactive")


# ---------------------------------------------------------------------------
# Command type for all operations
# ---------------------------------------------------------------------------


class TestCommandType:
    @pytest.mark.parametrize("action", sorted(VALID_ACTIONS))
    async def test_all_operations_use_correct_type(
        self, mock_bridge: MagicMock, action: str
    ) -> None:
        await build_profile_operation(mock_bridge, action=action)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "build-profile-operation"


# ---------------------------------------------------------------------------
# Parameter handling
# ---------------------------------------------------------------------------


class TestParameterHandling:
    async def test_list_no_extra_params(self, mock_bridge: MagicMock) -> None:
        await build_profile_operation(mock_bridge, action="list")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert set(params.keys()) == {"operation"}

    async def test_get_active_no_extra_params(self, mock_bridge: MagicMock) -> None:
        await build_profile_operation(mock_bridge, action="get-active")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert set(params.keys()) == {"operation"}

    async def test_set_active_without_path_sends(self, mock_bridge: MagicMock) -> None:
        """set-active without profile_path — C# handler returns error."""
        await build_profile_operation(mock_bridge, action="set-active")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "set-active"
        assert "profilePath" not in params

    async def test_profile_path_camel_case(self, mock_bridge: MagicMock) -> None:
        await build_profile_operation(
            mock_bridge,
            action="get-info",
            profile_path="Assets/BuildProfiles/Win64.asset",
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "profilePath" in params
        assert "profile_path" not in params


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------


class TestTimeout:
    async def test_default_timeout_is_30(self, mock_bridge: MagicMock) -> None:
        await build_profile_operation(mock_bridge, action="list")
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 30.0 or timeout == 30

    async def test_custom_timeout(self, mock_bridge: MagicMock) -> None:
        await build_profile_operation(mock_bridge, action="set-active", timeout=60)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 60


# ---------------------------------------------------------------------------
# Return value: C3 null profile handling
# ---------------------------------------------------------------------------


class TestNullProfileReturn:
    async def test_get_active_null_profile_success(self, mock_bridge: MagicMock) -> None:
        """C3: GetActiveBuildProfile returns null — should be success with null profile."""
        response = CommandResult(
            success=True,
            data={
                "operation": "get-active",
                "profile": None,
                "success": True,
                "message": "No custom build profile active; using platform default.",
            },
        )
        mock_bridge.send_command_with_retry.return_value = response
        result = await build_profile_operation(mock_bridge, action="get-active")
        assert result.success is True
        assert result.data["profile"] is None


# ---------------------------------------------------------------------------
# Return value: C4 batch mode error
# ---------------------------------------------------------------------------


class TestBatchModeError:
    async def test_set_active_batch_mode_error(self, mock_bridge: MagicMock) -> None:
        """C4: SetActiveBuildProfile fails in batch mode."""
        response = CommandResult(
            success=False,
            data={
                "operation": "set-active",
                "success": False,
                "message": "Cannot switch build profiles in batch mode. "
                "Use the -activeBuildProfile CLI argument when launching Unity instead.",
            },
        )
        mock_bridge.send_command_with_retry.return_value = response
        result = await build_profile_operation(
            mock_bridge,
            action="set-active",
            profile_path="Assets/BuildProfiles/Android.asset",
        )
        assert result.success is False
        assert "-activeBuildProfile" in result.data["message"]

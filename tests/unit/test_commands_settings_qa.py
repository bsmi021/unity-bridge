"""QA adversarial tests for commands/settings.py — PlayerSettings operations.

Tests edge cases, error paths, and spec compliance that the dev tests may miss.
Covers findings from docs/tech-spec-adversarial-review.md (M2, M3, M15).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from unity_bridge.commands.settings import (
    VALID_ACTIONS,
    player_settings_operation,
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
    """Verify that VALID_ACTIONS matches the spec exactly."""

    def test_all_spec_operations_present(self) -> None:
        expected = {"get", "set", "defines-list", "defines-add", "defines-remove"}
        assert VALID_ACTIONS == expected

    def test_is_frozenset(self) -> None:
        assert isinstance(VALID_ACTIONS, frozenset)


# ---------------------------------------------------------------------------
# Edge cases: invalid / boundary inputs
# ---------------------------------------------------------------------------


class TestEdgeCaseInputs:
    async def test_empty_string_action_raises(self, mock_bridge: MagicMock) -> None:
        with pytest.raises(ValueError, match="Invalid settings action"):
            await player_settings_operation(mock_bridge, action="")

    async def test_whitespace_only_action_raises(self, mock_bridge: MagicMock) -> None:
        with pytest.raises(ValueError, match="Invalid settings action"):
            await player_settings_operation(mock_bridge, action="   ")

    async def test_case_insensitive_action(self, mock_bridge: MagicMock) -> None:
        await player_settings_operation(mock_bridge, action="DEFINES-LIST")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "defines-list"

    async def test_mixed_case_action(self, mock_bridge: MagicMock) -> None:
        await player_settings_operation(mock_bridge, action="Defines-Add")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "defines-add"

    async def test_action_with_leading_trailing_whitespace(self, mock_bridge: MagicMock) -> None:
        await player_settings_operation(mock_bridge, action="  set  ")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "set"

    async def test_similar_but_invalid_action_raises(self, mock_bridge: MagicMock) -> None:
        with pytest.raises(ValueError, match="Invalid settings action"):
            await player_settings_operation(mock_bridge, action="gets")

    async def test_defines_without_hyphen_raises(self, mock_bridge: MagicMock) -> None:
        with pytest.raises(ValueError, match="Invalid settings action"):
            await player_settings_operation(mock_bridge, action="defineslist")


# ---------------------------------------------------------------------------
# Parameter exclusion: only set params are sent to bridge
# ---------------------------------------------------------------------------


class TestParameterExclusion:
    async def test_set_without_value_still_sends(self, mock_bridge: MagicMock) -> None:
        """set without value — the bridge should handle the error, not Python."""
        await player_settings_operation(mock_bridge, action="set", key="companyName")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "set"
        assert params["key"] == "companyName"
        assert "value" not in params

    async def test_defines_add_without_symbol_sends(self, mock_bridge: MagicMock) -> None:
        """defines-add without symbol — C# handler returns error."""
        await player_settings_operation(mock_bridge, action="defines-add", platform="Android")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "defines-add"
        assert params["platform"] == "Android"
        assert "symbol" not in params

    async def test_defines_remove_without_symbol_sends(self, mock_bridge: MagicMock) -> None:
        await player_settings_operation(mock_bridge, action="defines-remove", platform="iOS")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "defines-remove"
        assert "symbol" not in params

    async def test_get_with_empty_string_key_sends(self, mock_bridge: MagicMock) -> None:
        """Empty string key is still sent — it's not None."""
        await player_settings_operation(mock_bridge, action="get", key="")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["key"] == ""

    async def test_no_extra_params_for_defines_list(self, mock_bridge: MagicMock) -> None:
        await player_settings_operation(mock_bridge, action="defines-list")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert set(params.keys()) == {"operation"}


# ---------------------------------------------------------------------------
# Timeout edge cases
# ---------------------------------------------------------------------------


class TestTimeoutEdgeCases:
    async def test_zero_timeout(self, mock_bridge: MagicMock) -> None:
        await player_settings_operation(mock_bridge, action="get", timeout=0)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 0

    async def test_large_timeout(self, mock_bridge: MagicMock) -> None:
        await player_settings_operation(mock_bridge, action="get", timeout=999)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 999

    async def test_defines_add_should_use_longer_timeout(self, mock_bridge: MagicMock) -> None:
        """Per spec, defines-add triggers recompilation; callers may want 120s."""
        await player_settings_operation(
            mock_bridge,
            action="defines-add",
            symbol="X",
            platform="Standalone",
            timeout=120,
        )
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 120


# ---------------------------------------------------------------------------
# Return value propagation
# ---------------------------------------------------------------------------


class TestReturnValuePropagation:
    async def test_failure_result_propagated(self, mock_bridge: MagicMock) -> None:
        failed = CommandResult(
            success=False,
            data={"operation": "set", "success": False},
            error="Unknown setting key: badKey",
            exit_code=1,
        )
        mock_bridge.send_command_with_retry.return_value = failed
        result = await player_settings_operation(mock_bridge, action="set", key="badKey", value="x")
        assert result.success is False
        assert result.error == "Unknown setting key: badKey"

    async def test_defines_response_with_domain_reload(self, mock_bridge: MagicMock) -> None:
        """Verify the expected response shape is passed through."""
        response = CommandResult(
            success=True,
            data={
                "operation": "defines-add",
                "platform": "Standalone",
                "symbol": "MY_FEATURE",
                "defines": ["EXISTING", "MY_FEATURE"],
                "triggeredRecompilation": True,
                "domainReloadPending": True,
                "success": True,
            },
        )
        mock_bridge.send_command_with_retry.return_value = response
        result = await player_settings_operation(
            mock_bridge,
            action="defines-add",
            symbol="MY_FEATURE",
            platform="Standalone",
        )
        assert result.success is True
        assert result.data["domainReloadPending"] is True
        assert result.data["triggeredRecompilation"] is True


# ---------------------------------------------------------------------------
# Command type consistency
# ---------------------------------------------------------------------------


class TestCommandType:
    @pytest.mark.parametrize("action", sorted(VALID_ACTIONS))
    async def test_all_operations_use_correct_command_type(
        self, mock_bridge: MagicMock, action: str
    ) -> None:
        kwargs: dict[str, object] = {}
        if "add" in action or "remove" in action:
            kwargs["symbol"] = "TEST_SYM"
        if action == "set":
            kwargs["key"] = "companyName"
            kwargs["value"] = "Test"
        await player_settings_operation(mock_bridge, action=action, **kwargs)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "player-settings-operation"

"""Unit tests for commands/undo.py — all 6 undo operations + adversarial edge cases."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.commands.undo import (
    VALID_ACTIONS,
    undo_clear,
    undo_collapse,
    undo_group_name,
    undo_history,
    undo_perform,
    undo_redo,
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
# undo perform
# ---------------------------------------------------------------------------


class TestUndoPerform:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await undo_perform(mock_bridge)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "undo-operation"

    async def test_sends_perform_operation(self, mock_bridge: MagicMock) -> None:
        await undo_perform(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "perform"

    async def test_custom_timeout(self, mock_bridge: MagicMock) -> None:
        await undo_perform(mock_bridge, timeout=10.0)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 10.0

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        await undo_perform(mock_bridge)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 5.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        expected = CommandResult(
            success=True, data={"success": True, "undone": True, "groupName": "Move"}
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await undo_perform(mock_bridge)
        assert result.success is True
        assert result.data["undone"] is True

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await undo_perform(failing_bridge)
        assert result.success is False


# ---------------------------------------------------------------------------
# undo redo
# ---------------------------------------------------------------------------


class TestUndoRedo:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await undo_redo(mock_bridge)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "undo-operation"

    async def test_sends_redo_operation(self, mock_bridge: MagicMock) -> None:
        await undo_redo(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "redo"

    async def test_custom_timeout(self, mock_bridge: MagicMock) -> None:
        await undo_redo(mock_bridge, timeout=15.0)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 15.0

    async def test_returns_redo_result(self, mock_bridge: MagicMock) -> None:
        expected = CommandResult(
            success=True, data={"success": True, "redone": True, "groupName": "Move"}
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await undo_redo(mock_bridge)
        assert result.success is True
        assert result.data["redone"] is True

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await undo_redo(failing_bridge)
        assert result.success is False


# ---------------------------------------------------------------------------
# undo history
# ---------------------------------------------------------------------------


class TestUndoHistory:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await undo_history(mock_bridge)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "undo-operation"

    async def test_sends_history_operation(self, mock_bridge: MagicMock) -> None:
        await undo_history(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "history"

    async def test_default_limit(self, mock_bridge: MagicMock) -> None:
        await undo_history(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["limit"] == 20

    async def test_custom_limit(self, mock_bridge: MagicMock) -> None:
        await undo_history(mock_bridge, limit=5)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["limit"] == 5

    async def test_limit_zero(self, mock_bridge: MagicMock) -> None:
        """Edge case: limit=0 should still be sent (returns no entries)."""
        await undo_history(mock_bridge, limit=0)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["limit"] == 0

    async def test_limit_large(self, mock_bridge: MagicMock) -> None:
        """Edge case: very large limit (beyond the 100-entry rolling log)."""
        await undo_history(mock_bridge, limit=10000)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["limit"] == 10000

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await undo_history(failing_bridge)
        assert result.success is False


# ---------------------------------------------------------------------------
# undo clear
# ---------------------------------------------------------------------------


class TestUndoClear:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await undo_clear(mock_bridge)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "undo-operation"

    async def test_sends_clear_operation(self, mock_bridge: MagicMock) -> None:
        await undo_clear(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "clear"

    async def test_no_extra_params(self, mock_bridge: MagicMock) -> None:
        """Clear should only send operation, nothing else."""
        await undo_clear(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert set(params.keys()) == {"operation"}

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await undo_clear(failing_bridge)
        assert result.success is False


# ---------------------------------------------------------------------------
# undo group-name
# ---------------------------------------------------------------------------


class TestUndoGroupName:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await undo_group_name(mock_bridge)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "undo-operation"

    async def test_sends_group_name_operation(self, mock_bridge: MagicMock) -> None:
        await undo_group_name(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "group-name"

    async def test_no_extra_params(self, mock_bridge: MagicMock) -> None:
        await undo_group_name(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert set(params.keys()) == {"operation"}

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await undo_group_name(failing_bridge)
        assert result.success is False


# ---------------------------------------------------------------------------
# undo collapse
# ---------------------------------------------------------------------------


class TestUndoCollapse:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await undo_collapse(mock_bridge, group_index=5)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "undo-operation"

    async def test_sends_collapse_operation(self, mock_bridge: MagicMock) -> None:
        await undo_collapse(mock_bridge, group_index=5)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "collapse"

    async def test_sends_group_index(self, mock_bridge: MagicMock) -> None:
        await undo_collapse(mock_bridge, group_index=42)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["groupIndex"] == 42

    async def test_name_included_when_provided(self, mock_bridge: MagicMock) -> None:
        await undo_collapse(mock_bridge, group_index=5, name="AI: Refactor")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["name"] == "AI: Refactor"

    async def test_name_omitted_when_none(self, mock_bridge: MagicMock) -> None:
        await undo_collapse(mock_bridge, group_index=5)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "name" not in params

    async def test_group_index_zero(self, mock_bridge: MagicMock) -> None:
        """Edge case: group index 0 is valid."""
        await undo_collapse(mock_bridge, group_index=0)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["groupIndex"] == 0

    async def test_empty_name_string(self, mock_bridge: MagicMock) -> None:
        """Edge case: empty string is still sent as name."""
        await undo_collapse(mock_bridge, group_index=5, name="")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["name"] == ""

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await undo_collapse(failing_bridge, group_index=5)
        assert result.success is False


# ---------------------------------------------------------------------------
# VALID_ACTIONS constant
# ---------------------------------------------------------------------------


class TestValidActions:
    def test_all_six_operations_present(self) -> None:
        """Spec requires exactly 6 operations."""
        expected = {"perform", "redo", "history", "clear", "group-name", "collapse"}
        assert VALID_ACTIONS == expected

    def test_is_frozenset(self) -> None:
        """Should be immutable."""
        assert isinstance(VALID_ACTIONS, frozenset)


# ---------------------------------------------------------------------------
# Adversarial / edge case tests
# ---------------------------------------------------------------------------


class TestUndoAdversarial:
    async def test_all_operations_use_send_command_with_retry(self, mock_bridge: MagicMock) -> None:
        """All operations must use send_command_with_retry, not send_command."""
        await undo_perform(mock_bridge)
        await undo_redo(mock_bridge)
        await undo_history(mock_bridge)
        await undo_clear(mock_bridge)
        await undo_group_name(mock_bridge)
        await undo_collapse(mock_bridge, group_index=1)

        assert mock_bridge.send_command_with_retry.call_count == 6
        assert mock_bridge.send_command.call_count == 0

    async def test_all_operations_use_correct_command_type(self, mock_bridge: MagicMock) -> None:
        """Every call must target 'undo-operation'."""
        funcs = [
            lambda: undo_perform(mock_bridge),
            lambda: undo_redo(mock_bridge),
            lambda: undo_history(mock_bridge),
            lambda: undo_clear(mock_bridge),
            lambda: undo_group_name(mock_bridge),
            lambda: undo_collapse(mock_bridge, group_index=1),
        ]
        for func in funcs:
            await func()
            cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
            assert cmd == "undo-operation"

    async def test_history_negative_limit_still_sent(self, mock_bridge: MagicMock) -> None:
        """Python side should not validate limit — let C# handle it."""
        await undo_history(mock_bridge, limit=-1)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["limit"] == -1

    async def test_collapse_negative_group_index_still_sent(self, mock_bridge: MagicMock) -> None:
        """Python side should not validate groupIndex — let C# handle it."""
        await undo_collapse(mock_bridge, group_index=-5)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["groupIndex"] == -5

    async def test_collapse_name_with_special_chars(self, mock_bridge: MagicMock) -> None:
        """Names with special chars should be passed through as-is."""
        weird_name = 'AI: "Refactor" <Player> & {Components}'
        await undo_collapse(mock_bridge, group_index=1, name=weird_name)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["name"] == weird_name

    async def test_collapse_name_with_unicode(self, mock_bridge: MagicMock) -> None:
        """Unicode in group name should be passed through."""
        await undo_collapse(mock_bridge, group_index=1, name="AI: Refactoring")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "name" in params

    async def test_perform_only_sends_operation_param(self, mock_bridge: MagicMock) -> None:
        """Perform should only send the operation key, no extra params."""
        await undo_perform(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert set(params.keys()) == {"operation"}

    async def test_redo_only_sends_operation_param(self, mock_bridge: MagicMock) -> None:
        """Redo should only send the operation key, no extra params."""
        await undo_redo(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert set(params.keys()) == {"operation"}

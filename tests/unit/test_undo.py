"""Unit tests for commands/undo.py — undo/redo operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.core.bridge import CommandResult


def _import_undo():
    from unity_bridge.commands import undo

    return undo


# ---------------------------------------------------------------------------
# perform
# ---------------------------------------------------------------------------


class TestPerform:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        undo = _import_undo()
        await undo.undo_perform(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "undo-operation"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        undo = _import_undo()
        await undo.undo_perform(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params == {"operation": "perform"}

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        undo = _import_undo()
        await undo.undo_perform(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 5.0

    async def test_custom_timeout(self, mock_bridge: MagicMock) -> None:
        undo = _import_undo()
        await undo.undo_perform(mock_bridge, timeout=10.0)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 10.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        undo = _import_undo()
        expected = CommandResult(
            success=True,
            data={"undone": True, "groupName": "Set Transform.position"},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await undo.undo_perform(mock_bridge)
        assert result.success is True
        assert result.data["undone"] is True


# ---------------------------------------------------------------------------
# redo
# ---------------------------------------------------------------------------


class TestRedo:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        undo = _import_undo()
        await undo.undo_redo(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "undo-operation"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        undo = _import_undo()
        await undo.undo_redo(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params == {"operation": "redo"}

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        undo = _import_undo()
        await undo.undo_redo(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 5.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        undo = _import_undo()
        expected = CommandResult(
            success=True,
            data={"redone": True, "groupName": "Set Transform.position"},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await undo.undo_redo(mock_bridge)
        assert result.success is True
        assert result.data["redone"] is True


# ---------------------------------------------------------------------------
# history
# ---------------------------------------------------------------------------


class TestHistory:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        undo = _import_undo()
        await undo.undo_history(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "undo-operation"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        undo = _import_undo()
        await undo.undo_history(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params == {"operation": "history", "limit": 20}

    async def test_custom_limit(self, mock_bridge: MagicMock) -> None:
        undo = _import_undo()
        await undo.undo_history(mock_bridge, limit=5)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["limit"] == 5

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        undo = _import_undo()
        await undo.undo_history(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 5.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        undo = _import_undo()
        expected = CommandResult(
            success=True,
            data={
                "currentGroupName": "Set Transform.position",
                "recentOperations": [
                    {"name": "Set Transform.position", "id": 42},
                ],
                "count": 1,
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await undo.undo_history(mock_bridge)
        assert result.success is True
        assert result.data["count"] == 1


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------


class TestClear:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        undo = _import_undo()
        await undo.undo_clear(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "undo-operation"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        undo = _import_undo()
        await undo.undo_clear(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params == {"operation": "clear"}

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        undo = _import_undo()
        await undo.undo_clear(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 5.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        undo = _import_undo()
        expected = CommandResult(
            success=True,
            data={"cleared": True},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await undo.undo_clear(mock_bridge)
        assert result.success is True
        assert result.data["cleared"] is True


# ---------------------------------------------------------------------------
# group-name
# ---------------------------------------------------------------------------


class TestGroupName:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        undo = _import_undo()
        await undo.undo_group_name(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "undo-operation"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        undo = _import_undo()
        await undo.undo_group_name(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params == {"operation": "group-name"}

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        undo = _import_undo()
        await undo.undo_group_name(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 5.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        undo = _import_undo()
        expected = CommandResult(
            success=True,
            data={"groupName": "Set Transform.position"},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await undo.undo_group_name(mock_bridge)
        assert result.success is True
        assert result.data["groupName"] == "Set Transform.position"


# ---------------------------------------------------------------------------
# collapse
# ---------------------------------------------------------------------------


class TestCollapse:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        undo = _import_undo()
        await undo.undo_collapse(mock_bridge, group_index=42)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "undo-operation"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        undo = _import_undo()
        await undo.undo_collapse(mock_bridge, group_index=42)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params == {"operation": "collapse", "groupIndex": 42}

    async def test_includes_name_when_provided(self, mock_bridge: MagicMock) -> None:
        undo = _import_undo()
        await undo.undo_collapse(mock_bridge, group_index=42, name="AI: Refactor PlayerController")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "collapse"
        assert params["groupIndex"] == 42
        assert params["name"] == "AI: Refactor PlayerController"

    async def test_excludes_name_when_none(self, mock_bridge: MagicMock) -> None:
        undo = _import_undo()
        await undo.undo_collapse(mock_bridge, group_index=10)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert "name" not in params

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        undo = _import_undo()
        await undo.undo_collapse(mock_bridge, group_index=42)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 5.0

    async def test_custom_timeout(self, mock_bridge: MagicMock) -> None:
        undo = _import_undo()
        await undo.undo_collapse(mock_bridge, group_index=42, timeout=15.0)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 15.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        undo = _import_undo()
        expected = CommandResult(
            success=True,
            data={"collapsed": True, "groupIndex": 42, "name": "AI: Refactor"},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await undo.undo_collapse(mock_bridge, group_index=42)
        assert result.success is True
        assert result.data["collapsed"] is True


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

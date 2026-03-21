"""Unit tests for commands/prefs.py — EditorPrefs and SessionState."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.core.bridge import CommandResult


def _import_prefs():
    from unity_bridge.commands import prefs

    return prefs


# ---------------------------------------------------------------------------
# prefs_get
# ---------------------------------------------------------------------------


class TestPrefsGet:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_prefs()
        await mod.prefs_get(mock_bridge, key="MyKey")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "editor-prefs"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_prefs()
        await mod.prefs_get(mock_bridge, key="MyKey", value_type="int", scope="session")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "get"
        assert params["key"] == "MyKey"
        assert params["valueType"] == "int"
        assert params["scope"] == "session"

    async def test_default_scope(self, mock_bridge: MagicMock) -> None:
        mod = _import_prefs()
        await mod.prefs_get(mock_bridge, key="MyKey")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["scope"] == "prefs"
        assert params["valueType"] == "string"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_prefs()
        await mod.prefs_get(mock_bridge, key="MyKey")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 5.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_prefs()
        expected = CommandResult(
            success=True,
            data={"key": "MyKey", "value": "42", "valueType": "int"},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.prefs_get(mock_bridge, key="MyKey")
        assert result.success is True
        assert result.data["value"] == "42"


# ---------------------------------------------------------------------------
# prefs_set
# ---------------------------------------------------------------------------


class TestPrefsSet:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_prefs()
        await mod.prefs_set(mock_bridge, key="MyKey", value="hello")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "editor-prefs"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_prefs()
        await mod.prefs_set(
            mock_bridge, key="Score", value="100", value_type="int", scope="session"
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "set"
        assert params["key"] == "Score"
        assert params["value"] == "100"
        assert params["valueType"] == "int"
        assert params["scope"] == "session"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_prefs()
        await mod.prefs_set(mock_bridge, key="K", value="V")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 5.0


# ---------------------------------------------------------------------------
# prefs_delete
# ---------------------------------------------------------------------------


class TestPrefsDelete:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_prefs()
        await mod.prefs_delete(mock_bridge, key="OldKey")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "editor-prefs"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_prefs()
        await mod.prefs_delete(mock_bridge, key="OldKey", scope="session")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "delete"
        assert params["key"] == "OldKey"
        assert params["scope"] == "session"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        mod = _import_prefs()
        await mod.prefs_delete(mock_bridge, key="OldKey")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 5.0


# ---------------------------------------------------------------------------
# prefs_has
# ---------------------------------------------------------------------------


class TestPrefsHas:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        mod = _import_prefs()
        await mod.prefs_has(mock_bridge, key="TestKey")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "editor-prefs"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        mod = _import_prefs()
        await mod.prefs_has(mock_bridge, key="TestKey")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "has"
        assert params["key"] == "TestKey"
        assert params["scope"] == "prefs"

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        mod = _import_prefs()
        expected = CommandResult(
            success=True,
            data={"key": "TestKey", "exists": True},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await mod.prefs_has(mock_bridge, key="TestKey")
        assert result.success is True
        assert result.data["exists"] is True


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

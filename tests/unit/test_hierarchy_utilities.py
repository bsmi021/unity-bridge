"""Unit tests for commands/hierarchy.py — GameObject utility operations (Phase 2)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.core.bridge import CommandResult


def _import_hierarchy():
    from unity_bridge.commands import hierarchy

    return hierarchy


# ---------------------------------------------------------------------------
# missing-scripts
# ---------------------------------------------------------------------------


class TestMissingScripts:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        h = _import_hierarchy()
        await h.missing_scripts(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "gameobject-utility"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        h = _import_hierarchy()
        await h.missing_scripts(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "missing-scripts"
        assert params["fix"] is False

    async def test_fix_flag(self, mock_bridge: MagicMock) -> None:
        h = _import_hierarchy()
        await h.missing_scripts(mock_bridge, fix=True)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["fix"] is True

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        h = _import_hierarchy()
        await h.missing_scripts(mock_bridge)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 15.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        h = _import_hierarchy()
        expected = CommandResult(
            success=True,
            data={"found": [], "totalCount": 0, "removed": 0},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await h.missing_scripts(mock_bridge)
        assert result.success is True
        assert result.data["totalCount"] == 0


# ---------------------------------------------------------------------------
# static-flags
# ---------------------------------------------------------------------------


class TestStaticFlags:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        h = _import_hierarchy()
        await h.static_flags(mock_bridge, object_path="Environment/Building")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "gameobject-utility"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        h = _import_hierarchy()
        await h.static_flags(mock_bridge, object_path="Environment/Building")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "static-flags"
        assert params["gameObjectPath"] == "Environment/Building"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        h = _import_hierarchy()
        await h.static_flags(mock_bridge, object_path="Environment/Building")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 15.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        h = _import_hierarchy()
        expected = CommandResult(
            success=True,
            data={"flags": ["BatchingStatic", "OccluderStatic"], "rawValue": 14},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await h.static_flags(mock_bridge, object_path="Environment/Building")
        assert result.success is True
        assert "BatchingStatic" in result.data["flags"]


# ---------------------------------------------------------------------------
# set-static-flags
# ---------------------------------------------------------------------------


class TestSetStaticFlags:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        h = _import_hierarchy()
        await h.set_static_flags(
            mock_bridge,
            object_path="Environment/Building",
            flags=["BatchingStatic", "NavigationStatic"],
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "gameobject-utility"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        h = _import_hierarchy()
        await h.set_static_flags(
            mock_bridge,
            object_path="Environment/Building",
            flags=["BatchingStatic", "NavigationStatic"],
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "set-static-flags"
        assert params["gameObjectPath"] == "Environment/Building"
        assert params["flags"] == ["BatchingStatic", "NavigationStatic"]

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        h = _import_hierarchy()
        await h.set_static_flags(mock_bridge, object_path="Building", flags=["BatchingStatic"])
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 15.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        h = _import_hierarchy()
        expected = CommandResult(
            success=True,
            data={"flags": ["BatchingStatic"], "changed": True},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await h.set_static_flags(
            mock_bridge, object_path="Building", flags=["BatchingStatic"]
        )
        assert result.success is True
        assert result.data["changed"] is True


# ---------------------------------------------------------------------------
# set-layer
# ---------------------------------------------------------------------------


class TestSetLayer:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        h = _import_hierarchy()
        await h.set_layer(mock_bridge, object_path="Player", layer=8)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "gameobject-utility"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        h = _import_hierarchy()
        await h.set_layer(mock_bridge, object_path="Player", layer=8)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "set-layer"
        assert params["gameObjectPath"] == "Player"
        assert params["layer"] == 8
        assert params["recursive"] is False

    async def test_recursive_flag(self, mock_bridge: MagicMock) -> None:
        h = _import_hierarchy()
        await h.set_layer(mock_bridge, object_path="Player", layer=8, recursive=True)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["recursive"] is True

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        h = _import_hierarchy()
        await h.set_layer(mock_bridge, object_path="Player", layer=8)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 15.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        h = _import_hierarchy()
        expected = CommandResult(
            success=True,
            data={"path": "Player", "layer": 8, "affectedCount": 5},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await h.set_layer(mock_bridge, object_path="Player", layer=8)
        assert result.success is True
        assert result.data["affectedCount"] == 5


# ---------------------------------------------------------------------------
# set-tag
# ---------------------------------------------------------------------------


class TestSetTag:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        h = _import_hierarchy()
        await h.set_tag(mock_bridge, object_path="Player", tag="Player")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "gameobject-utility"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        h = _import_hierarchy()
        await h.set_tag(mock_bridge, object_path="Player", tag="Player")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "set-tag"
        assert params["gameObjectPath"] == "Player"
        assert params["tag"] == "Player"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        h = _import_hierarchy()
        await h.set_tag(mock_bridge, object_path="Player", tag="Player")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 15.0

    async def test_custom_timeout(self, mock_bridge: MagicMock) -> None:
        h = _import_hierarchy()
        await h.set_tag(mock_bridge, object_path="Player", tag="Player", timeout=30.0)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 30.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        h = _import_hierarchy()
        expected = CommandResult(
            success=True,
            data={"path": "Player", "tag": "Player", "changed": True},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await h.set_tag(mock_bridge, object_path="Player", tag="Player")
        assert result.success is True
        assert result.data["changed"] is True


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

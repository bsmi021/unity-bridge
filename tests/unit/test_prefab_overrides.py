"""Unit tests for commands/prefab.py — prefab override operations (Phase 2)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.core.bridge import CommandResult


def _import_prefab():
    from unity_bridge.commands import prefab

    return prefab


# ---------------------------------------------------------------------------
# overrides list
# ---------------------------------------------------------------------------


class TestOverridesList:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        prefab = _import_prefab()
        await prefab.prefab_overrides_list(mock_bridge, instance_path="Player")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "prefab-override"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        prefab = _import_prefab()
        await prefab.prefab_overrides_list(mock_bridge, instance_path="Player")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "list"
        assert params["instancePath"] == "Player"
        assert params["includeDefaultOverrides"] is False

    async def test_include_default_overrides(self, mock_bridge: MagicMock) -> None:
        prefab = _import_prefab()
        await prefab.prefab_overrides_list(
            mock_bridge, instance_path="Player", include_default_overrides=True
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["includeDefaultOverrides"] is True

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        prefab = _import_prefab()
        await prefab.prefab_overrides_list(mock_bridge, instance_path="Player")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 30.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        prefab = _import_prefab()
        expected = CommandResult(
            success=True,
            data={"hasOverrides": True, "count": 2},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await prefab.prefab_overrides_list(mock_bridge, instance_path="Player")
        assert result.success is True
        assert result.data["hasOverrides"] is True


# ---------------------------------------------------------------------------
# overrides apply
# ---------------------------------------------------------------------------


class TestOverridesApply:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        prefab = _import_prefab()
        await prefab.prefab_overrides_apply(mock_bridge, instance_path="Player")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "prefab-override"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        prefab = _import_prefab()
        await prefab.prefab_overrides_apply(mock_bridge, instance_path="Player")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "apply"
        assert params["instancePath"] == "Player"
        assert "target" not in params

    async def test_with_target(self, mock_bridge: MagicMock) -> None:
        prefab = _import_prefab()
        await prefab.prefab_overrides_apply(
            mock_bridge,
            instance_path="Player",
            target="PropertyModification:Transform",
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["target"] == "PropertyModification:Transform"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        prefab = _import_prefab()
        await prefab.prefab_overrides_apply(mock_bridge, instance_path="Player")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 30.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        prefab = _import_prefab()
        expected = CommandResult(success=True, data={"applied": True, "count": 4})
        mock_bridge.send_command_with_retry.return_value = expected
        result = await prefab.prefab_overrides_apply(mock_bridge, instance_path="Player")
        assert result.success is True
        assert result.data["applied"] is True


# ---------------------------------------------------------------------------
# overrides revert
# ---------------------------------------------------------------------------


class TestOverridesRevert:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        prefab = _import_prefab()
        await prefab.prefab_overrides_revert(mock_bridge, instance_path="Player")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "prefab-override"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        prefab = _import_prefab()
        await prefab.prefab_overrides_revert(mock_bridge, instance_path="Player")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "revert"
        assert params["instancePath"] == "Player"
        assert "target" not in params

    async def test_with_target(self, mock_bridge: MagicMock) -> None:
        prefab = _import_prefab()
        await prefab.prefab_overrides_revert(
            mock_bridge,
            instance_path="Player",
            target="AddedComponent:AudioSource",
        )
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["target"] == "AddedComponent:AudioSource"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        prefab = _import_prefab()
        await prefab.prefab_overrides_revert(mock_bridge, instance_path="Player")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 30.0


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


class TestStatus:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        prefab = _import_prefab()
        await prefab.prefab_status(mock_bridge, path="Player")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "prefab-override"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        prefab = _import_prefab()
        await prefab.prefab_status(mock_bridge, path="Player")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "status"
        assert params["instancePath"] == "Player"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        prefab = _import_prefab()
        await prefab.prefab_status(mock_bridge, path="Player")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 30.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        prefab = _import_prefab()
        expected = CommandResult(
            success=True,
            data={
                "prefabType": "Regular",
                "instanceStatus": "Connected",
                "isVariant": False,
            },
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await prefab.prefab_status(mock_bridge, path="Player")
        assert result.success is True
        assert result.data["prefabType"] == "Regular"


# ---------------------------------------------------------------------------
# find-instances
# ---------------------------------------------------------------------------


class TestFindInstances:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        prefab = _import_prefab()
        await prefab.prefab_find_instances(mock_bridge, asset_path="Assets/Prefabs/Enemy.prefab")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "prefab-override"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        prefab = _import_prefab()
        await prefab.prefab_find_instances(mock_bridge, asset_path="Assets/Prefabs/Enemy.prefab")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "find-instances"
        assert params["assetPath"] == "Assets/Prefabs/Enemy.prefab"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        prefab = _import_prefab()
        await prefab.prefab_find_instances(mock_bridge, asset_path="Assets/Prefabs/Enemy.prefab")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 30.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        prefab = _import_prefab()
        expected = CommandResult(
            success=True,
            data={"instances": [{"path": "Enemy (1)", "scene": "Level1.unity"}], "count": 1},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await prefab.prefab_find_instances(
            mock_bridge, asset_path="Assets/Prefabs/Enemy.prefab"
        )
        assert result.success is True
        assert result.data["count"] == 1


# ---------------------------------------------------------------------------
# unpack
# ---------------------------------------------------------------------------


class TestUnpack:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        prefab = _import_prefab()
        await prefab.prefab_unpack(mock_bridge, instance_path="Player")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_command_type(call_args) == "prefab-override"

    async def test_sends_correct_parameters(self, mock_bridge: MagicMock) -> None:
        prefab = _import_prefab()
        await prefab.prefab_unpack(mock_bridge, instance_path="Player")
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["operation"] == "unpack"
        assert params["instancePath"] == "Player"
        assert params["completely"] is False

    async def test_completely_flag(self, mock_bridge: MagicMock) -> None:
        prefab = _import_prefab()
        await prefab.prefab_unpack(mock_bridge, instance_path="Player", completely=True)
        call_args = mock_bridge.send_command_with_retry.call_args
        params = _extract_parameters(call_args)
        assert params["completely"] is True

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        prefab = _import_prefab()
        await prefab.prefab_unpack(mock_bridge, instance_path="Player")
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 30.0

    async def test_custom_timeout(self, mock_bridge: MagicMock) -> None:
        prefab = _import_prefab()
        await prefab.prefab_unpack(mock_bridge, instance_path="Player", timeout=60.0)
        call_args = mock_bridge.send_command_with_retry.call_args
        assert _extract_kwarg(call_args, "timeout") == 60.0

    async def test_returns_command_result(self, mock_bridge: MagicMock) -> None:
        prefab = _import_prefab()
        expected = CommandResult(
            success=True,
            data={"unpacked": True, "mode": "OutermostRoot"},
        )
        mock_bridge.send_command_with_retry.return_value = expected
        result = await prefab.prefab_unpack(mock_bridge, instance_path="Player")
        assert result.success is True
        assert result.data["unpacked"] is True


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

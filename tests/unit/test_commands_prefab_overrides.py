"""Unit tests for prefab override operations in commands/prefab.py — adversarial QA."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.commands.prefab import (
    prefab_find_instances,
    prefab_overrides_apply,
    prefab_overrides_list,
    prefab_overrides_revert,
    prefab_status,
    prefab_unpack,
)


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
# prefab overrides list
# ---------------------------------------------------------------------------


class TestPrefabOverridesList:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await prefab_overrides_list(mock_bridge, "Player")
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "prefab-override"

    async def test_sends_list_operation(self, mock_bridge: MagicMock) -> None:
        await prefab_overrides_list(mock_bridge, "Player")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "list"

    async def test_sends_instance_path(self, mock_bridge: MagicMock) -> None:
        await prefab_overrides_list(mock_bridge, "Environment/Light")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["instancePath"] == "Environment/Light"

    async def test_include_default_overrides_false(self, mock_bridge: MagicMock) -> None:
        """M4: Default should be includeDefaultOverrides=false."""
        await prefab_overrides_list(mock_bridge, "Player")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["includeDefaultOverrides"] is False

    async def test_include_default_overrides_true(self, mock_bridge: MagicMock) -> None:
        await prefab_overrides_list(mock_bridge, "Player", include_default_overrides=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["includeDefaultOverrides"] is True

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await prefab_overrides_list(failing_bridge, "Player")
        assert result.success is False


# ---------------------------------------------------------------------------
# prefab overrides apply
# ---------------------------------------------------------------------------


class TestPrefabOverridesApply:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await prefab_overrides_apply(mock_bridge, "Player")
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "prefab-override"

    async def test_sends_apply_operation(self, mock_bridge: MagicMock) -> None:
        await prefab_overrides_apply(mock_bridge, "Player")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "apply"

    async def test_apply_all_no_target(self, mock_bridge: MagicMock) -> None:
        await prefab_overrides_apply(mock_bridge, "Player")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "target" not in params

    async def test_apply_specific_target(self, mock_bridge: MagicMock) -> None:
        await prefab_overrides_apply(mock_bridge, "Player", target="PropertyModification:Transform")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["target"] == "PropertyModification:Transform"

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await prefab_overrides_apply(failing_bridge, "Player")
        assert result.success is False


# ---------------------------------------------------------------------------
# prefab overrides revert
# ---------------------------------------------------------------------------


class TestPrefabOverridesRevert:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await prefab_overrides_revert(mock_bridge, "Player")
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "prefab-override"

    async def test_sends_revert_operation(self, mock_bridge: MagicMock) -> None:
        await prefab_overrides_revert(mock_bridge, "Player")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "revert"

    async def test_revert_all_no_target(self, mock_bridge: MagicMock) -> None:
        await prefab_overrides_revert(mock_bridge, "Player")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "target" not in params

    async def test_revert_specific_target(self, mock_bridge: MagicMock) -> None:
        await prefab_overrides_revert(mock_bridge, "Player", target="AddedComponent:AudioSource")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["target"] == "AddedComponent:AudioSource"

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await prefab_overrides_revert(failing_bridge, "Player")
        assert result.success is False


# ---------------------------------------------------------------------------
# prefab status
# ---------------------------------------------------------------------------


class TestPrefabStatus:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await prefab_status(mock_bridge, "Player")
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "prefab-override"

    async def test_sends_status_operation(self, mock_bridge: MagicMock) -> None:
        await prefab_status(mock_bridge, "Player")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "status"

    async def test_sends_instance_path(self, mock_bridge: MagicMock) -> None:
        await prefab_status(mock_bridge, "Environment/Tree")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["instancePath"] == "Environment/Tree"

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await prefab_status(failing_bridge, "Player")
        assert result.success is False


# ---------------------------------------------------------------------------
# prefab find-instances
# ---------------------------------------------------------------------------


class TestPrefabFindInstances:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await prefab_find_instances(mock_bridge, "Assets/Prefabs/Enemy.prefab")
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "prefab-override"

    async def test_sends_find_instances_operation(self, mock_bridge: MagicMock) -> None:
        await prefab_find_instances(mock_bridge, "Assets/Prefabs/Enemy.prefab")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "find-instances"

    async def test_sends_asset_path(self, mock_bridge: MagicMock) -> None:
        await prefab_find_instances(mock_bridge, "Assets/Prefabs/Player.prefab")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["assetPath"] == "Assets/Prefabs/Player.prefab"

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await prefab_find_instances(failing_bridge, "Assets/Prefabs/Missing.prefab")
        assert result.success is False


# ---------------------------------------------------------------------------
# prefab unpack
# ---------------------------------------------------------------------------


class TestPrefabUnpack:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await prefab_unpack(mock_bridge, "Player")
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "prefab-override"

    async def test_sends_unpack_operation(self, mock_bridge: MagicMock) -> None:
        await prefab_unpack(mock_bridge, "Player")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "unpack"

    async def test_default_not_completely(self, mock_bridge: MagicMock) -> None:
        await prefab_unpack(mock_bridge, "Player")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["completely"] is False

    async def test_completely_flag(self, mock_bridge: MagicMock) -> None:
        await prefab_unpack(mock_bridge, "Player", completely=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["completely"] is True

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await prefab_unpack(failing_bridge, "Player")
        assert result.success is False


# ---------------------------------------------------------------------------
# Adversarial edge cases
# ---------------------------------------------------------------------------


class TestPrefabOverridesAdversarial:
    async def test_all_operations_use_send_command_with_retry(self, mock_bridge: MagicMock) -> None:
        """All operations must use send_command_with_retry."""
        await prefab_overrides_list(mock_bridge, "P")
        await prefab_overrides_apply(mock_bridge, "P")
        await prefab_overrides_revert(mock_bridge, "P")
        await prefab_status(mock_bridge, "P")
        await prefab_find_instances(mock_bridge, "Assets/P.prefab")
        await prefab_unpack(mock_bridge, "P")

        assert mock_bridge.send_command_with_retry.call_count == 6
        assert mock_bridge.send_command.call_count == 0

    async def test_all_operations_target_prefab_override(self, mock_bridge: MagicMock) -> None:
        """Every call must target 'prefab-override' command type."""
        funcs = [
            lambda: prefab_overrides_list(mock_bridge, "P"),
            lambda: prefab_overrides_apply(mock_bridge, "P"),
            lambda: prefab_overrides_revert(mock_bridge, "P"),
            lambda: prefab_status(mock_bridge, "P"),
            lambda: prefab_find_instances(mock_bridge, "Assets/P.prefab"),
            lambda: prefab_unpack(mock_bridge, "P"),
        ]
        for func in funcs:
            await func()
            cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
            assert cmd == "prefab-override"

    async def test_path_with_special_chars(self, mock_bridge: MagicMock) -> None:
        """Paths with spaces and special chars should pass through."""
        await prefab_overrides_list(mock_bridge, "Environment/Light (1)")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["instancePath"] == "Environment/Light (1)"

    async def test_deeply_nested_path(self, mock_bridge: MagicMock) -> None:
        """Deeply nested hierarchy paths should pass through."""
        path = "Root/Parent/Child/Grandchild/Target"
        await prefab_status(mock_bridge, path)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["instancePath"] == path

    async def test_find_instances_non_prefab_asset(self, mock_bridge: MagicMock) -> None:
        """Non-prefab asset paths should still be sent (C# validates)."""
        await prefab_find_instances(mock_bridge, "Assets/Materials/Red.mat")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["assetPath"] == "Assets/Materials/Red.mat"

    async def test_apply_with_empty_target(self, mock_bridge: MagicMock) -> None:
        """Empty string target is still sent (different from None)."""
        await prefab_overrides_apply(mock_bridge, "P", target="")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["target"] == ""

    async def test_in_timeout_defaults(self) -> None:
        """prefab-override should be in TIMEOUT_DEFAULTS."""
        from unity_bridge.core.protocol import TIMEOUT_DEFAULTS

        assert "prefab-override" in TIMEOUT_DEFAULTS

    async def test_not_in_parallel_safe(self) -> None:
        """prefab-override is a mutating command, should NOT be parallel safe."""
        from unity_bridge.core.protocol import PARALLEL_SAFE_COMMANDS

        assert "prefab-override" not in PARALLEL_SAFE_COMMANDS

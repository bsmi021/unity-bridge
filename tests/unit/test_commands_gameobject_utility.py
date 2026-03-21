"""Unit tests for gameobject utility operations in commands/hierarchy.py — adversarial QA."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unity_bridge.commands.hierarchy import (
    missing_scripts,
    set_layer,
    set_static_flags,
    set_tag,
    static_flags,
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
# missing-scripts
# ---------------------------------------------------------------------------


class TestMissingScripts:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await missing_scripts(mock_bridge)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "gameobject-utility"

    async def test_sends_missing_scripts_operation(self, mock_bridge: MagicMock) -> None:
        await missing_scripts(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "missing-scripts"

    async def test_default_fix_false(self, mock_bridge: MagicMock) -> None:
        await missing_scripts(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["fix"] is False

    async def test_fix_true(self, mock_bridge: MagicMock) -> None:
        await missing_scripts(mock_bridge, fix=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["fix"] is True

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        await missing_scripts(mock_bridge)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 15.0

    async def test_custom_timeout(self, mock_bridge: MagicMock) -> None:
        await missing_scripts(mock_bridge, timeout=60.0)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 60.0

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await missing_scripts(failing_bridge)
        assert result.success is False


# ---------------------------------------------------------------------------
# static-flags
# ---------------------------------------------------------------------------


class TestStaticFlags:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await static_flags(mock_bridge, "Player")
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "gameobject-utility"

    async def test_sends_static_flags_operation(self, mock_bridge: MagicMock) -> None:
        await static_flags(mock_bridge, "Player")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "static-flags"

    async def test_sends_object_path(self, mock_bridge: MagicMock) -> None:
        await static_flags(mock_bridge, "Environment/Tree")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["gameObjectPath"] == "Environment/Tree"

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await static_flags(failing_bridge, "Player")
        assert result.success is False


# ---------------------------------------------------------------------------
# set-static-flags
# ---------------------------------------------------------------------------


class TestSetStaticFlags:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await set_static_flags(mock_bridge, "Player", ["BatchingStatic"])
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "gameobject-utility"

    async def test_sends_set_static_flags_operation(self, mock_bridge: MagicMock) -> None:
        await set_static_flags(mock_bridge, "Player", ["BatchingStatic"])
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "set-static-flags"

    async def test_sends_flags_list(self, mock_bridge: MagicMock) -> None:
        flags = ["BatchingStatic", "NavigationStatic", "OccludeeStatic"]
        await set_static_flags(mock_bridge, "Player", flags)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["flags"] == flags

    async def test_sends_object_path(self, mock_bridge: MagicMock) -> None:
        await set_static_flags(mock_bridge, "Environment/Rock", ["BatchingStatic"])
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["gameObjectPath"] == "Environment/Rock"

    async def test_empty_flags_clears_all(self, mock_bridge: MagicMock) -> None:
        """Empty list should clear all flags (C# builds 0 from empty list)."""
        await set_static_flags(mock_bridge, "Player", [])
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["flags"] == []

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await set_static_flags(failing_bridge, "Player", ["BatchingStatic"])
        assert result.success is False


# ---------------------------------------------------------------------------
# set-layer
# ---------------------------------------------------------------------------


class TestSetLayer:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await set_layer(mock_bridge, "Player", 8)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "gameobject-utility"

    async def test_sends_set_layer_operation(self, mock_bridge: MagicMock) -> None:
        await set_layer(mock_bridge, "Player", 8)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "set-layer"

    async def test_sends_layer_value(self, mock_bridge: MagicMock) -> None:
        await set_layer(mock_bridge, "Player", 12)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["layer"] == 12

    async def test_default_not_recursive(self, mock_bridge: MagicMock) -> None:
        await set_layer(mock_bridge, "Player", 8)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["recursive"] is False

    async def test_recursive_flag(self, mock_bridge: MagicMock) -> None:
        await set_layer(mock_bridge, "Player", 8, recursive=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["recursive"] is True

    async def test_sends_object_path(self, mock_bridge: MagicMock) -> None:
        await set_layer(mock_bridge, "Environment/Water", 4)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["gameObjectPath"] == "Environment/Water"

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await set_layer(failing_bridge, "Player", 8)
        assert result.success is False


# ---------------------------------------------------------------------------
# set-tag
# ---------------------------------------------------------------------------


class TestSetTag:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await set_tag(mock_bridge, "Player", "Player")
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "gameobject-utility"

    async def test_sends_set_tag_operation(self, mock_bridge: MagicMock) -> None:
        await set_tag(mock_bridge, "Player", "Player")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "set-tag"

    async def test_sends_tag_value(self, mock_bridge: MagicMock) -> None:
        await set_tag(mock_bridge, "Enemy", "Enemy")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["tag"] == "Enemy"

    async def test_sends_object_path(self, mock_bridge: MagicMock) -> None:
        await set_tag(mock_bridge, "Environment/Pickup", "Collectible")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["gameObjectPath"] == "Environment/Pickup"

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await set_tag(failing_bridge, "Player", "Player")
        assert result.success is False


# ---------------------------------------------------------------------------
# Adversarial edge cases
# ---------------------------------------------------------------------------


class TestGameObjectUtilityAdversarial:
    async def test_all_operations_use_send_command_with_retry(self, mock_bridge: MagicMock) -> None:
        """All operations must use send_command_with_retry."""
        await missing_scripts(mock_bridge)
        await static_flags(mock_bridge, "P")
        await set_static_flags(mock_bridge, "P", ["BatchingStatic"])
        await set_layer(mock_bridge, "P", 0)
        await set_tag(mock_bridge, "P", "Untagged")

        assert mock_bridge.send_command_with_retry.call_count == 5
        assert mock_bridge.send_command.call_count == 0

    async def test_all_operations_target_gameobject_utility(self, mock_bridge: MagicMock) -> None:
        """Every call must target 'gameobject-utility' command type."""
        funcs = [
            lambda: missing_scripts(mock_bridge),
            lambda: static_flags(mock_bridge, "P"),
            lambda: set_static_flags(mock_bridge, "P", []),
            lambda: set_layer(mock_bridge, "P", 0),
            lambda: set_tag(mock_bridge, "P", "Untagged"),
        ]
        for func in funcs:
            await func()
            cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
            assert cmd == "gameobject-utility"

    async def test_path_with_special_chars(self, mock_bridge: MagicMock) -> None:
        """Paths with spaces and special chars should pass through."""
        await static_flags(mock_bridge, "Environment/Light (1)")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["gameObjectPath"] == "Environment/Light (1)"

    async def test_deeply_nested_path(self, mock_bridge: MagicMock) -> None:
        """Deeply nested hierarchy paths should pass through."""
        path = "Root/Parent/Child/Grandchild/Target"
        await set_tag(mock_bridge, path, "Deep")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["gameObjectPath"] == path

    async def test_layer_zero_valid(self, mock_bridge: MagicMock) -> None:
        """Layer 0 (Default) is a valid layer index."""
        await set_layer(mock_bridge, "Player", 0)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["layer"] == 0

    async def test_layer_31_max(self, mock_bridge: MagicMock) -> None:
        """Layer 31 is the maximum Unity layer index."""
        await set_layer(mock_bridge, "Player", 31)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["layer"] == 31

    async def test_tag_untagged(self, mock_bridge: MagicMock) -> None:
        """'Untagged' is a valid built-in tag."""
        await set_tag(mock_bridge, "Player", "Untagged")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["tag"] == "Untagged"

    async def test_all_seven_static_flags(self, mock_bridge: MagicMock) -> None:
        """All 7 StaticEditorFlags should be sendable."""
        all_flags = [
            "ContributeGI",
            "OccluderStatic",
            "BatchingStatic",
            "NavigationStatic",
            "OccludeeStatic",
            "OffMeshLinkGeneration",
            "ReflectionProbeStatic",
        ]
        await set_static_flags(mock_bridge, "Terrain", all_flags)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["flags"] == all_flags

    async def test_not_in_parallel_safe(self) -> None:
        """gameobject-utility has mutating operations, should NOT be parallel safe."""
        from unity_bridge.core.protocol import PARALLEL_SAFE_COMMANDS

        assert "gameobject-utility" not in PARALLEL_SAFE_COMMANDS

    async def test_in_timeout_defaults(self) -> None:
        """gameobject-utility should be in TIMEOUT_DEFAULTS."""
        from unity_bridge.core.protocol import TIMEOUT_DEFAULTS

        assert "gameobject-utility" in TIMEOUT_DEFAULTS

    async def test_missing_scripts_no_gameobjectpath_needed(self, mock_bridge: MagicMock) -> None:
        """missing-scripts scans all objects — no gameObjectPath required."""
        await missing_scripts(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "gameObjectPath" not in params

    async def test_set_layer_recursive_true_sends_correctly(self, mock_bridge: MagicMock) -> None:
        """Recursive set-layer should send recursive=True."""
        await set_layer(mock_bridge, "Environment", 5, recursive=True)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["recursive"] is True
        assert params["layer"] == 5

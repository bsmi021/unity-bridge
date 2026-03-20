"""Unit tests for commands/compile_extended.py — all 4 compilation pipeline ops + adversarial."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from unity_bridge.commands.compile_extended import (
    VALID_OPERATIONS,
    compilation_pipeline_operation,
    compile_assemblies,
    compile_defines,
    compile_optimization,
    compile_which,
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
# compile assemblies
# ---------------------------------------------------------------------------


class TestCompileAssemblies:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await compile_assemblies(mock_bridge)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "compilation-pipeline"

    async def test_sends_assemblies_operation(self, mock_bridge: MagicMock) -> None:
        await compile_assemblies(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "assemblies"

    async def test_default_timeout(self, mock_bridge: MagicMock) -> None:
        await compile_assemblies(mock_bridge)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 15.0

    async def test_custom_timeout(self, mock_bridge: MagicMock) -> None:
        await compile_assemblies(mock_bridge, timeout=30.0)
        timeout = _extract_kwarg(mock_bridge.send_command_with_retry.call_args, "timeout")
        assert timeout == 30.0

    async def test_no_extra_params(self, mock_bridge: MagicMock) -> None:
        await compile_assemblies(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert set(params.keys()) == {"operation"}

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await compile_assemblies(failing_bridge)
        assert result.success is False


# ---------------------------------------------------------------------------
# compile defines
# ---------------------------------------------------------------------------


class TestCompileDefines:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await compile_defines(mock_bridge, "Assembly-CSharp")
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "compilation-pipeline"

    async def test_sends_defines_operation(self, mock_bridge: MagicMock) -> None:
        await compile_defines(mock_bridge, "Assembly-CSharp")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "defines"

    async def test_sends_assembly_name(self, mock_bridge: MagicMock) -> None:
        await compile_defines(mock_bridge, "Assembly-CSharp-Editor")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["assemblyName"] == "Assembly-CSharp-Editor"

    async def test_empty_assembly_name_still_sent(self, mock_bridge: MagicMock) -> None:
        """Empty name is sent; C# handler validates and rejects."""
        await compile_defines(mock_bridge, "")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["assemblyName"] == ""

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await compile_defines(failing_bridge, "NonExistent")
        assert result.success is False


# ---------------------------------------------------------------------------
# compile which
# ---------------------------------------------------------------------------


class TestCompileWhich:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await compile_which(mock_bridge, "Assets/Scripts/Player.cs")
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "compilation-pipeline"

    async def test_sends_which_operation(self, mock_bridge: MagicMock) -> None:
        await compile_which(mock_bridge, "Assets/Scripts/Player.cs")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "which"

    async def test_sends_script_path(self, mock_bridge: MagicMock) -> None:
        await compile_which(mock_bridge, "Assets/Scripts/Combat/DamageSystem.cs")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["scriptPath"] == "Assets/Scripts/Combat/DamageSystem.cs"

    async def test_path_with_spaces(self, mock_bridge: MagicMock) -> None:
        """Paths with spaces should be passed through."""
        await compile_which(mock_bridge, "Assets/My Scripts/Player Controller.cs")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["scriptPath"] == "Assets/My Scripts/Player Controller.cs"

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await compile_which(failing_bridge, "Assets/Missing.cs")
        assert result.success is False


# ---------------------------------------------------------------------------
# compile optimization
# ---------------------------------------------------------------------------


class TestCompileOptimization:
    async def test_sends_correct_command_type(self, mock_bridge: MagicMock) -> None:
        await compile_optimization(mock_bridge)
        cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
        assert cmd == "compilation-pipeline"

    async def test_sends_optimization_operation(self, mock_bridge: MagicMock) -> None:
        await compile_optimization(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "optimization"

    async def test_get_mode_no_mode_param(self, mock_bridge: MagicMock) -> None:
        """Getting current mode should not include 'mode' in params."""
        await compile_optimization(mock_bridge)
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "mode" not in params

    async def test_set_mode_debug(self, mock_bridge: MagicMock) -> None:
        await compile_optimization(mock_bridge, mode="Debug")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["mode"] == "Debug"

    async def test_set_mode_release(self, mock_bridge: MagicMock) -> None:
        await compile_optimization(mock_bridge, mode="Release")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["mode"] == "Release"

    async def test_set_mode_none(self, mock_bridge: MagicMock) -> None:
        """m3: CodeOptimization enum has 3 values including None."""
        await compile_optimization(mock_bridge, mode="None")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["mode"] == "None"

    async def test_bridge_error_propagated(self, failing_bridge: MagicMock) -> None:
        result = await compile_optimization(failing_bridge, mode="Debug")
        assert result.success is False


# ---------------------------------------------------------------------------
# Generic operation dispatch
# ---------------------------------------------------------------------------


class TestCompilationPipelineOperation:
    async def test_assemblies_dispatch(self, mock_bridge: MagicMock) -> None:
        await compilation_pipeline_operation(mock_bridge, "assemblies")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "assemblies"

    async def test_defines_dispatch(self, mock_bridge: MagicMock) -> None:
        await compilation_pipeline_operation(
            mock_bridge, "defines", assembly_name="Assembly-CSharp"
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "defines"
        assert params["assemblyName"] == "Assembly-CSharp"

    async def test_which_dispatch(self, mock_bridge: MagicMock) -> None:
        await compilation_pipeline_operation(
            mock_bridge, "which", script_path="Assets/Scripts/Player.cs"
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "which"
        assert params["scriptPath"] == "Assets/Scripts/Player.cs"

    async def test_optimization_dispatch_get(self, mock_bridge: MagicMock) -> None:
        await compilation_pipeline_operation(mock_bridge, "optimization")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "optimization"
        assert "mode" not in params

    async def test_optimization_dispatch_set(self, mock_bridge: MagicMock) -> None:
        await compilation_pipeline_operation(mock_bridge, "optimization", mode="Release")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["mode"] == "Release"

    async def test_invalid_operation_raises(self, mock_bridge: MagicMock) -> None:
        with pytest.raises(ValueError, match="Invalid compilation pipeline"):
            await compilation_pipeline_operation(mock_bridge, "invalid-op")

    async def test_case_insensitive_operation(self, mock_bridge: MagicMock) -> None:
        """Operation should be lowercased before sending."""
        await compilation_pipeline_operation(mock_bridge, "ASSEMBLIES")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "assemblies"

    async def test_extra_whitespace_stripped(self, mock_bridge: MagicMock) -> None:
        """Extra whitespace in operation should be handled."""
        await compilation_pipeline_operation(mock_bridge, "  defines  ")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["operation"] == "defines"

    async def test_none_params_omitted(self, mock_bridge: MagicMock) -> None:
        """None values for optional params should not be included."""
        await compilation_pipeline_operation(
            mock_bridge,
            "defines",
            assembly_name="Test",
            script_path=None,
            mode=None,
        )
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert "scriptPath" not in params
        assert "mode" not in params
        assert params["assemblyName"] == "Test"


# ---------------------------------------------------------------------------
# VALID_OPERATIONS constant
# ---------------------------------------------------------------------------


class TestValidOperations:
    def test_all_four_operations_present(self) -> None:
        expected = {"assemblies", "defines", "which", "optimization"}
        assert VALID_OPERATIONS == expected

    def test_is_frozenset(self) -> None:
        assert isinstance(VALID_OPERATIONS, frozenset)


# ---------------------------------------------------------------------------
# Adversarial edge cases
# ---------------------------------------------------------------------------


class TestCompileAdversarial:
    async def test_all_operations_use_send_command_with_retry(self, mock_bridge: MagicMock) -> None:
        await compile_assemblies(mock_bridge)
        await compile_defines(mock_bridge, "Test")
        await compile_which(mock_bridge, "Assets/Test.cs")
        await compile_optimization(mock_bridge)

        assert mock_bridge.send_command_with_retry.call_count == 4
        assert mock_bridge.send_command.call_count == 0

    async def test_all_operations_target_compilation_pipeline(self, mock_bridge: MagicMock) -> None:
        funcs = [
            lambda: compile_assemblies(mock_bridge),
            lambda: compile_defines(mock_bridge, "Test"),
            lambda: compile_which(mock_bridge, "Assets/Test.cs"),
            lambda: compile_optimization(mock_bridge),
        ]
        for func in funcs:
            await func()
            cmd = _extract_command_type(mock_bridge.send_command_with_retry.call_args)
            assert cmd == "compilation-pipeline"

    async def test_m9_not_in_parallel_safe(self) -> None:
        """M9: compilation-pipeline must NOT be in PARALLEL_SAFE_COMMANDS."""
        from unity_bridge.core.protocol import PARALLEL_SAFE_COMMANDS

        assert "compilation-pipeline" not in PARALLEL_SAFE_COMMANDS

    async def test_defines_special_chars_in_assembly_name(self, mock_bridge: MagicMock) -> None:
        """Assembly names with dots and hyphens should pass through."""
        await compile_defines(mock_bridge, "MyGame.Tests-Editor")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["assemblyName"] == "MyGame.Tests-Editor"

    async def test_which_backslash_path(self, mock_bridge: MagicMock) -> None:
        """Windows-style paths should be passed through as-is."""
        await compile_which(mock_bridge, "Assets\\Scripts\\Player.cs")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["scriptPath"] == "Assets\\Scripts\\Player.cs"

    async def test_optimization_invalid_mode_still_sent(self, mock_bridge: MagicMock) -> None:
        """Python side should not validate mode — let C# reject invalid values."""
        await compile_optimization(mock_bridge, mode="InvalidMode")
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["mode"] == "InvalidMode"

    async def test_in_timeout_defaults(self) -> None:
        """compilation-pipeline should be in TIMEOUT_DEFAULTS."""
        from unity_bridge.core.protocol import TIMEOUT_DEFAULTS

        assert "compilation-pipeline" in TIMEOUT_DEFAULTS

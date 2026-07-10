"""Regression tests for the bounded Phase 3 parity repairs."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from typer.testing import CliRunner

from unity_bridge.app import app
from unity_bridge.commands import console, diagnostics, editor, hierarchy, prefab


ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / "ClaudeCodeBridge"


def _parameters(bridge: MagicMock) -> dict[str, Any]:
    return bridge.send_command_with_retry.call_args.kwargs["parameters"]


async def test_focus_sends_inverse_frame_selection_contract(mock_bridge: MagicMock) -> None:
    # Arrange / Act
    await editor.focus_object(mock_bridge, "Player", no_frame=True)

    # Assert
    assert _parameters(mock_bridge) == {
        "gameObjectPath": "Player",
        "frameSelection": False,
    }


async def test_refresh_sends_force_update_contract(mock_bridge: MagicMock) -> None:
    # Arrange / Act
    await editor.refresh_assets(mock_bridge, force=True)

    # Assert
    assert _parameters(mock_bridge) == {"forceUpdate": True}


async def test_get_component_serializes_field_names_as_list(mock_bridge: MagicMock) -> None:
    # Arrange / Act
    await hierarchy.get_component(mock_bridge, "Player", "Transform", "position, rotation")

    # Assert
    assert _parameters(mock_bridge)["fieldNames"] == ["position", "rotation"]


async def test_set_component_serializes_field_update_contract(mock_bridge: MagicMock) -> None:
    # Arrange / Act
    await hierarchy.set_component(
        mock_bridge,
        "Player",
        "Health",
        ["current:10", 'label:"ready"'],
    )

    # Assert
    assert _parameters(mock_bridge)["fieldUpdates"] == [
        {"fieldName": "current", "valueJson": "10"},
        {"fieldName": "label", "valueJson": '"ready"'},
    ]


async def test_console_uses_csharp_stack_limit_and_filter_contract(
    mock_bridge: MagicMock,
) -> None:
    # Arrange / Act
    await console.console_read(mock_bridge, pattern="Null.*", max_stack_lines=8)

    # Assert
    assert _parameters(mock_bridge) == {
        "filterPattern": "Null.*",
        "maxStackTraceLines": 8,
    }
    source = (BRIDGE / "ReadConsoleCommandHandler.cs").read_text(encoding="utf-8")
    models = (BRIDGE / "BridgeModelsPhase3.cs").read_text(encoding="utf-8")
    assert "public string filterPattern;" in models
    assert "filterRegex.IsMatch(processedMessage)" in source
    assert "RegexOptions.None" in source
    assert "TimeSpan.FromSeconds(1)" in source


async def test_profiler_cpu_flag_controls_frame_timing_contract(
    mock_bridge: MagicMock,
) -> None:
    # Arrange / Act
    await diagnostics.profiler_sample(mock_bridge, cpu=True)

    # Assert
    assert _parameters(mock_bridge)["includeCPU"] is True
    models = (BRIDGE / "BridgeModels.cs").read_text(encoding="utf-8")
    handler = (BRIDGE / "ProfilerSampleCommandHandler.cs").read_text(encoding="utf-8")
    assert "public bool includeCPU = false;" in models
    assert "if (parameters.includeCPU)" in handler


async def test_prefab_position_is_explicit_and_applied_by_handler(
    mock_bridge: MagicMock,
) -> None:
    # Arrange / Act
    await prefab.prefab_instantiate(mock_bridge, "Assets/Enemy.prefab", (1.0, 2.0, 3.0))

    # Assert
    assert _parameters(mock_bridge)["position"] == {
        "x": 1.0,
        "y": 2.0,
        "z": 3.0,
        "isSet": True,
    }
    models = (BRIDGE / "BridgeModelsPhase3.cs").read_text(encoding="utf-8")
    handler = (BRIDGE / "PrefabOperationCommandHandler.cs").read_text(encoding="utf-8")
    assert "public SerializableVector3 position;" in models
    assert "parameters.position.isSet" in handler
    assert "instance.transform.position" in handler


def test_prefab_destroy_has_reachable_validated_dispatch() -> None:
    # Arrange
    handler = (BRIDGE / "PrefabOperationCommandHandler.cs").read_text(encoding="utf-8")
    helpers = (BRIDGE / "PrefabOperationHelpers.cs").read_text(encoding="utf-8")

    # Act / Assert
    assert 'case "destroy":' in handler
    assert "DestroyPrefabInstance(parameters)" in handler
    assert "PrefabUtility.IsPartOfPrefabInstance" in helpers
    assert "Undo.DestroyObjectImmediate" in helpers


def test_authored_build_platform_operations_are_dispatched() -> None:
    # Arrange
    handler = (BRIDGE / "BuildOperationCommandHandler.cs").read_text(encoding="utf-8")

    # Act / Assert
    assert 'case "switch-platform":' in handler
    assert "return SwitchPlatform(command, parameters);" in handler
    assert 'case "list-platforms":' in handler
    assert "return ListPlatforms(command);" in handler


def test_build_platform_operations_are_exact_cli_leaves() -> None:
    # Arrange
    runner = CliRunner()

    # Act
    switch_help = runner.invoke(app, ["build", "switch-platform", "--help"])
    list_help = runner.invoke(app, ["build", "list-platforms", "--help"])

    # Assert
    assert switch_help.exit_code == 0, switch_help.output
    assert "Usage: unity-bridge build switch-platform" in switch_help.output
    assert list_help.exit_code == 0, list_help.output
    assert "Usage: unity-bridge build list-platforms" in list_help.output

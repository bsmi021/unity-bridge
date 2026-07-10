"""Exact Phase 0 CLI reachability and Python/C# wire-contract tests."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from typer import Typer
from typer.testing import CliRunner

from unity_bridge.app import app
from unity_bridge.commands import animation, asset_extended, editor, terrain, tilemap
from unity_bridge.core.output import OutputFormatter
from unity_bridge.core.protocol import PARALLEL_SAFE_COMMANDS, TIMEOUT_DEFAULTS


CLI_PATHS = (
    ("animation", "set-curve"),
    ("animation", "add-event"),
    ("animation", "set-properties"),
    ("terrain", "set-heights"),
    ("terrain", "set-settings"),
    ("tilemap", "fill-box"),
    ("tilemap", "compress-bounds"),
    ("asset-ext", "reserialize"),
)


def _state(mock_bridge: MagicMock) -> SimpleNamespace:
    return SimpleNamespace(bridge=mock_bridge, formatter=OutputFormatter())


def _run(cli: Typer, args: list[str], mock_bridge: MagicMock):
    return CliRunner().invoke(cli, args, obj=_state(mock_bridge))


def _parameters(mock_bridge: MagicMock) -> dict[str, Any]:
    call = mock_bridge.send_command_with_retry.call_args
    return call.kwargs["parameters"] if call.kwargs else call.args[1]


@pytest.mark.parametrize(("group", "command"), CLI_PATHS)
def test_exact_cli_path_has_help(group: str, command: str) -> None:
    """Arrange a required path; act on root help; assert exact registration."""
    result = CliRunner().invoke(app, [group, command, "--help"])

    assert result.exit_code == 0, result.output
    assert f"Usage: unity-bridge {group} {command}" in result.output


async def test_menu_wire_field_matches_csharp_model(mock_bridge: MagicMock) -> None:
    """Arrange validation; act through core; assert exact C# field name."""
    await editor.execute_menu_item(mock_bridge, "Assets/Create/Folder", validate_only=True)
    menu_params = _parameters(mock_bridge)

    assert menu_params == {
        "menuPath": "Assets/Create/Folder",
        "validate": True,
    }


async def test_screenshot_wire_field_matches_csharp_model(mock_bridge: MagicMock) -> None:
    """Arrange camera capture; act through core; assert exact C# field name."""
    await editor.capture_screenshot(
        mock_bridge,
        "Screenshots/camera.png",
        camera="Player/Main Camera",
    )
    screenshot_params = _parameters(mock_bridge)

    assert screenshot_params == {
        "outputPath": "Screenshots/camera.png",
        "cameraPath": "Player/Main Camera",
    }


def test_bridge_status_replaces_stale_health_check_policy() -> None:
    """Arrange protocol policy; act by lookup; assert registered command membership."""
    assert TIMEOUT_DEFAULTS["bridge-status"] == 5
    assert "bridge-status" in PARALLEL_SAFE_COMMANDS
    assert "health-check" not in TIMEOUT_DEFAULTS
    assert "health-check" not in PARALLEL_SAFE_COMMANDS


def test_animation_set_curve_cli_serializes_exact_payload(mock_bridge: MagicMock) -> None:
    result = _run(
        animation.animation_app,
        [
            "set-curve",
            "Assets/Anim/Walk.anim",
            "m_LocalPosition.y",
            "--keyframes",
            '[{"time":0.0,"value":0.0},{"time":1.0,"value":2.0}]',
            "--relative-path",
            "Rig/Hips",
            "--component-type",
            "Transform",
        ],
        mock_bridge,
    )

    assert result.exit_code == 0, result.output
    assert _parameters(mock_bridge) == {
        "operation": "set-curve",
        "clipPath": "Assets/Anim/Walk.anim",
        "propertyName": "m_LocalPosition.y",
        "keyframes": [
            {"time": 0.0, "value": 0.0},
            {"time": 1.0, "value": 2.0},
        ],
        "relativePath": "Rig/Hips",
        "componentType": "Transform",
    }


@pytest.mark.parametrize(
    "keyframes_json",
    (
        "not-json",
        "[]",
        '[{"time":0}]',
        '[{"time":"soon","value":1}]',
        '[{"time":true,"value":1}]',
    ),
)
def test_animation_set_curve_cli_rejects_invalid_keyframes(
    keyframes_json: str,
    mock_bridge: MagicMock,
) -> None:
    result = _run(
        animation.animation_app,
        [
            "set-curve",
            "Assets/Anim/Walk.anim",
            "m_LocalPosition.y",
            "--keyframes",
            keyframes_json,
        ],
        mock_bridge,
    )

    assert result.exit_code == 2
    assert not mock_bridge.send_command_with_retry.called


def test_animation_add_event_cli_serializes_exact_payload(mock_bridge: MagicMock) -> None:
    result = _run(
        animation.animation_app,
        [
            "add-event",
            "Assets/Anim/Walk.anim",
            "--time",
            "0.5",
            "--function",
            "FootStep",
            "--string-param",
            "left",
            "--int-param",
            "2",
            "--float-param",
            "0.75",
        ],
        mock_bridge,
    )

    assert result.exit_code == 0, result.output
    assert _parameters(mock_bridge) == {
        "operation": "add-event",
        "clipPath": "Assets/Anim/Walk.anim",
        "eventTime": 0.5,
        "eventFunction": "FootStep",
        "eventStringParam": "left",
        "eventIntParam": 2,
        "eventFloatParam": 0.75,
    }


def test_animation_set_properties_cli_serializes_exact_payload(
    mock_bridge: MagicMock,
) -> None:
    result = _run(
        animation.animation_app,
        [
            "set-properties",
            "Assets/Anim/Walk.anim",
            "--loop",
            "--wrap-mode",
            "Loop",
            "--frame-rate",
            "30",
        ],
        mock_bridge,
    )

    assert result.exit_code == 0, result.output
    assert _parameters(mock_bridge) == {
        "operation": "set-properties",
        "clipPath": "Assets/Anim/Walk.anim",
        "looping": True,
        "setLooping": True,
        "wrapMode": "Loop",
        "frameRate": 30.0,
    }


def test_terrain_set_heights_cli_serializes_exact_payload(mock_bridge: MagicMock) -> None:
    result = _run(
        terrain.terrain_app,
        [
            "set-heights",
            "--heights",
            "[[0.1,0.2],[0.3,0.4]]",
            "--x",
            "4",
            "--y",
            "6",
            "--terrain-name",
            "Island",
        ],
        mock_bridge,
    )

    assert result.exit_code == 0, result.output
    assert _parameters(mock_bridge) == {
        "operation": "set-heights",
        "heightX": 4,
        "heightY": 6,
        "heights": [
            {"values": [0.1, 0.2]},
            {"values": [0.3, 0.4]},
        ],
        "terrainName": "Island",
    }


@pytest.mark.parametrize(
    "heights_json",
    ("not-json", "[]", "[[]]", "[[0],[1,2]]", '[["high"]]', "[[true]]"),
)
def test_terrain_set_heights_cli_rejects_invalid_arrays(
    heights_json: str,
    mock_bridge: MagicMock,
) -> None:
    result = _run(
        terrain.terrain_app,
        ["set-heights", "--heights", heights_json],
        mock_bridge,
    )

    assert result.exit_code == 2
    assert not mock_bridge.send_command_with_retry.called


def test_terrain_set_settings_cli_serializes_exact_payload(mock_bridge: MagicMock) -> None:
    result = _run(
        terrain.terrain_app,
        [
            "set-settings",
            "--size",
            "500,100,600",
            "--heightmap-resolution",
            "513",
            "--terrain-name",
            "Island",
        ],
        mock_bridge,
    )

    assert result.exit_code == 0, result.output
    assert _parameters(mock_bridge) == {
        "operation": "set-settings",
        "terrainName": "Island",
        "sizeX": 500.0,
        "sizeY": 100.0,
        "sizeZ": 600.0,
        "heightmapResolution": 513,
    }


@pytest.mark.parametrize("size", ("500,100", "500,high,600"))
def test_terrain_set_settings_cli_rejects_invalid_size(
    size: str,
    mock_bridge: MagicMock,
) -> None:
    result = _run(
        terrain.terrain_app,
        ["set-settings", "--size", size],
        mock_bridge,
    )

    assert result.exit_code == 2
    assert not mock_bridge.send_command_with_retry.called


def test_tilemap_fill_box_cli_serializes_exact_payload(mock_bridge: MagicMock) -> None:
    result = _run(
        tilemap.tilemap_app,
        [
            "fill-box",
            "Grid/Ground",
            "Assets/Tiles/Grass.asset",
            "--start-x",
            "-2",
            "--start-y",
            "-1",
            "--end-x",
            "8",
            "--end-y",
            "9",
        ],
        mock_bridge,
    )

    assert result.exit_code == 0, result.output
    assert _parameters(mock_bridge) == {
        "operation": "fill-box",
        "tilemapPath": "Grid/Ground",
        "tilePath": "Assets/Tiles/Grass.asset",
        "startX": -2,
        "startY": -1,
        "endX": 8,
        "endY": 9,
    }


def test_tilemap_compress_bounds_cli_serializes_exact_payload(
    mock_bridge: MagicMock,
) -> None:
    result = _run(
        tilemap.tilemap_app,
        ["compress-bounds", "Grid/Ground"],
        mock_bridge,
    )

    assert result.exit_code == 0, result.output
    assert _parameters(mock_bridge) == {
        "operation": "compress-bounds",
        "tilemapPath": "Grid/Ground",
    }


def test_asset_reserialize_cli_serializes_exact_payload(mock_bridge: MagicMock) -> None:
    result = _run(
        asset_extended.asset_ext_app,
        [
            "reserialize",
            "--paths",
            "Assets/A.prefab",
            "--paths",
            "Assets/B.mat",
            "--mode",
            "metadata",
        ],
        mock_bridge,
    )

    assert result.exit_code == 0, result.output
    assert _parameters(mock_bridge) == {
        "operation": "reserialize",
        "assetPaths": ["Assets/A.prefab", "Assets/B.mat"],
        "reserializeMode": "metadata",
    }


def test_asset_reserialize_cli_rejects_invalid_mode(mock_bridge: MagicMock) -> None:
    result = _run(
        asset_extended.asset_ext_app,
        ["reserialize", "--mode", "invalid"],
        mock_bridge,
    )

    assert result.exit_code == 2
    assert not mock_bridge.send_command_with_retry.called

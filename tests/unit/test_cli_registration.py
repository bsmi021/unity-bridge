"""CLI registration tests for late-phase command groups."""

from __future__ import annotations

from unity_bridge.app import app
from unity_bridge.commands.hierarchy import component_app


def _registered_group_names() -> set[str]:
    return {group.name for group in app.registered_groups}


def _registered_command_names() -> set[str]:
    return {command.name for command in app.registered_commands}


def _component_command_names() -> set[str]:
    return {command.name for command in component_app.registered_commands}


def test_late_phase_command_groups_are_registered() -> None:
    """Phase 4-6 modules with Typer apps are exposed from the root CLI."""
    expected_groups = {
        "adaptive-performance",
        "addressables",
        "animation-clip",
        "audio-settings",
        "clipboard",
        "deep-serialize",
        "environment-settings",
        "entities",
        "game-view",
        "graphics-settings",
        "graphics-state",
        "graph-toolkit",
        "cloud",
        "input-system",
        "multiplayer-playmode",
        "navmesh",
        "object-identity",
        "occlusion",
        "operation",
        "preset",
        "physics2d",
        "profiler-control",
        "project-auditor",
        "reflection-probe",
        "render-pipeline",
        "scene-template",
        "scene-state",
        "scene-view",
        "script-execution-order",
        "script-info",
        "search",
        "terrain",
        "tilemap",
        "time-settings",
        "ui-toolkit",
        "window",
    }

    assert expected_groups <= _registered_group_names()


def test_late_phase_top_level_commands_are_registered() -> None:
    """Late-phase modules that expose commands instead of apps are reachable."""
    expected_commands = {
        "assembly-lock",
        "assembly-status",
        "assembly-unlock",
        "find-references",
        "sync-solution",
    }

    assert expected_commands <= _registered_command_names()


def test_component_extension_commands_are_imported() -> None:
    """Component copy/paste/reset commands are attached to the component group."""
    expected_commands = {"copy", "paste", "reset"}

    assert expected_commands <= _component_command_names()

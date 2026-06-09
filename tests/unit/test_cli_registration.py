"""CLI registration tests for late-phase command groups."""

from __future__ import annotations

import logging

from unity_bridge import app as app_module
from unity_bridge.app import app
from unity_bridge.commands.hierarchy import component_app


def _registered_group_names() -> set[str]:
    return {group.name for group in app.registered_groups}


def _registered_command_names() -> set[str]:
    return {command.name for command in app.registered_commands}


def _component_command_names() -> set[str]:
    return {command.name for command in component_app.registered_commands}


def test_failed_group_registration_is_logged_not_silent(caplog) -> None:
    """U5: a registration failure must surface as a warning, not vanish silently."""
    with caplog.at_level(logging.WARNING, logger="unity_bridge"):
        app_module._try_register_group(
            "unity_bridge.commands.does_not_exist", "nope_app", "ghost"
        )
    assert any("ghost" in rec.message for rec in caplog.records)
    # And it must not raise or actually register the group.
    assert "ghost" not in _registered_group_names()


def test_failed_command_registration_is_logged(caplog) -> None:
    """U5: a missing attribute on an existing module is surfaced, not swallowed."""
    with caplog.at_level(logging.WARNING, logger="unity_bridge"):
        app_module._try_register_command(
            "unity_bridge.commands.batch", "no_such_attr", "ghostcmd"
        )
    assert any("ghostcmd" in rec.message for rec in caplog.records)


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

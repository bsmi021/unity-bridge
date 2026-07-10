"""Unit tests for the environment-gated live Unity 6.5 fixture layer."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from tests.integration.live_unity import (
    CliInvocation,
    LiveFixtureUnavailable,
    OPTIONAL_ADAPTER_PROBES,
    load_fixture_matrix,
    require_explicit_guard,
    run_unity_cli,
    select_live_unity_environment,
    select_live_unity_role,
    select_live_unity_target,
)


def _status_result(
    *,
    healthy: bool = True,
    ready: bool | None = None,
    version: str = "6000.5.1f1",
    returncode: int = 0,
) -> CliInvocation:
    payload = {
        "success": healthy,
        "data": {
            "healthy": healthy,
            "ready": healthy if ready is None else ready,
            "unity_version": version,
        },
    }
    return CliInvocation(
        args=("status",),
        returncode=returncode,
        stdout=json.dumps(payload),
        stderr="",
        payload=payload,
    )


def _unity_project(tmp_path: Path) -> Path:
    project = tmp_path / "FixtureProject"
    (project / "Assets").mkdir(parents=True)
    (project / "ProjectSettings").mkdir()
    return project


def test_run_unity_cli_uses_explicit_project_and_bounded_timeout(
    tmp_path: Path,
) -> None:
    project = _unity_project(tmp_path)
    captured: dict[str, Any] = {}

    def execute(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured.update(kwargs)
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='{"success":true,"data":{"ok":true}}',
            stderr="",
        )

    result = run_unity_cli(
        project,
        ("scene-view", "get"),
        timeout=12,
        execute=execute,
    )

    assert captured["command"][-5:] == [
        "--no-color",
        "--project",
        str(project.resolve()),
        "scene-view",
        "get",
    ]
    assert captured["timeout"] == 12
    assert captured["shell"] is False
    assert result.require_success() == {"ok": True}


def test_run_unity_cli_records_non_json_output(tmp_path: Path) -> None:
    project = _unity_project(tmp_path)

    def execute(command: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 5, stdout="not-json", stderr="broken")

    result = run_unity_cli(project, ("status",), timeout=5, execute=execute)

    assert result.returncode == 5
    assert result.payload is None


@pytest.mark.parametrize("timeout", (0, -1, 601))
def test_run_unity_cli_rejects_unbounded_timeout(tmp_path: Path, timeout: int) -> None:
    project = _unity_project(tmp_path)

    with pytest.raises(ValueError, match="between 1 and 600"):
        run_unity_cli(project, ("status",), timeout=timeout)


def test_cli_invocation_require_success_reports_command_failure() -> None:
    invocation = CliInvocation(
        args=("profile", "info", "Assets/Missing.asset"),
        returncode=1,
        stdout='{"success":false,"error":"not found"}',
        stderr="",
        payload={"success": False, "error": "not found"},
    )

    with pytest.raises(AssertionError, match="profile info Assets/Missing.asset"):
        invocation.require_success()


def test_select_target_requires_environment_variable() -> None:
    with pytest.raises(LiveFixtureUnavailable, match="UNITY_BRIDGE_PROJECT is unset"):
        select_live_unity_target({}, runner=lambda *_args, **_kwargs: _status_result())


def test_select_target_requires_unity_project_shape(tmp_path: Path) -> None:
    empty = tmp_path / "NotUnity"
    empty.mkdir()

    with pytest.raises(LiveFixtureUnavailable, match="not a Unity project"):
        select_live_unity_target(
            {"UNITY_BRIDGE_PROJECT": str(empty)},
            runner=lambda *_args, **_kwargs: _status_result(),
        )


def test_select_target_requires_healthy_heartbeat(tmp_path: Path) -> None:
    project = _unity_project(tmp_path)

    with pytest.raises(LiveFixtureUnavailable, match="heartbeat is not healthy"):
        select_live_unity_target(
            {"UNITY_BRIDGE_PROJECT": str(project)},
            runner=lambda *_args, **_kwargs: _status_result(healthy=False, returncode=2),
        )


def test_select_target_requires_ready_editor(tmp_path: Path) -> None:
    project = _unity_project(tmp_path)

    with pytest.raises(LiveFixtureUnavailable, match="not command-ready"):
        select_live_unity_target(
            {"UNITY_BRIDGE_PROJECT": str(project)},
            runner=lambda *_args, **_kwargs: _status_result(ready=False),
        )


def test_select_target_requires_unity_6000_5(tmp_path: Path) -> None:
    project = _unity_project(tmp_path)

    with pytest.raises(LiveFixtureUnavailable, match="requires Unity 6000.5.x"):
        select_live_unity_target(
            {"UNITY_BRIDGE_PROJECT": str(project)},
            runner=lambda *_args, **_kwargs: _status_result(version="6000.4.0f1"),
        )


def test_select_target_rejects_invalid_status_json(tmp_path: Path) -> None:
    project = _unity_project(tmp_path)
    invalid = CliInvocation(
        args=("status",),
        returncode=0,
        stdout="not-json",
        stderr="",
        payload=None,
    )

    with pytest.raises(LiveFixtureUnavailable, match="valid JSON"):
        select_live_unity_target(
            {"UNITY_BRIDGE_PROJECT": str(project)},
            runner=lambda *_args, **_kwargs: invalid,
        )


def test_select_target_reports_status_probe_timeout(tmp_path: Path) -> None:
    project = _unity_project(tmp_path)

    def runner(*_args: Any, **_kwargs: Any) -> CliInvocation:
        raise subprocess.TimeoutExpired("unity-bridge status", 15)

    with pytest.raises(LiveFixtureUnavailable, match="status probe failed"):
        select_live_unity_target(
            {"UNITY_BRIDGE_PROJECT": str(project)},
            runner=runner,
        )


def test_select_target_returns_versioned_runner(tmp_path: Path) -> None:
    project = _unity_project(tmp_path)
    calls: list[tuple[str, ...]] = []

    def runner(
        _project: Path,
        args: tuple[str, ...],
        *,
        timeout: int,
    ) -> CliInvocation:
        calls.append(args)
        assert timeout == 15
        return _status_result()

    target = select_live_unity_target(
        {"UNITY_BRIDGE_PROJECT": str(project)},
        runner=runner,
    )

    assert target.project == project.resolve()
    assert target.unity_version == "6000.5.1f1"
    assert target.health["healthy"] is True
    assert calls == [("status",)]


def test_live_target_invocation_uses_selected_project(tmp_path: Path) -> None:
    project = _unity_project(tmp_path)
    calls: list[tuple[Path, tuple[str, ...], int]] = []

    def runner(
        selected: Path,
        args: tuple[str, ...],
        *,
        timeout: int,
    ) -> CliInvocation:
        calls.append((selected, args, timeout))
        if args == ("status",):
            return _status_result()
        payload = {"success": True, "data": {"validated": True}}
        return CliInvocation(args, 0, json.dumps(payload), "", payload)

    target = select_live_unity_target(
        {"UNITY_BRIDGE_PROJECT": str(project)},
        runner=runner,
    )
    result = target.invoke("menu", "Edit/Play", "--validate-only", timeout=22)

    assert result.require_success() == {"validated": True}
    assert calls[-1] == (
        project.resolve(),
        ("menu", "Edit/Play", "--validate-only"),
        22,
    )


def test_fixture_matrix_manifest_records_required_roles() -> None:
    roles = load_fixture_matrix()

    assert [(role.name, role.environment) for role in roles] == [
        ("core-clean", "UNITY_BRIDGE_CORE_CLEAN_PROJECT"),
        ("package-rich", "UNITY_BRIDGE_PACKAGE_RICH_PROJECT"),
        ("playback-build-target", "UNITY_BRIDGE_PLAYBACK_BUILD_TARGET_PROJECT"),
    ]


def test_select_role_reports_exact_missing_environment() -> None:
    with pytest.raises(
        LiveFixtureUnavailable,
        match=(
            "package-rich fixture role is unavailable: UNITY_BRIDGE_PACKAGE_RICH_PROJECT is unset"
        ),
    ):
        select_live_unity_role(
            "package-rich",
            {},
            runner=lambda *_args, **_kwargs: _status_result(),
        )


def test_select_role_uses_manifest_environment(tmp_path: Path) -> None:
    project = _unity_project(tmp_path)
    calls: list[tuple[Path, tuple[str, ...], int]] = []

    def runner(
        selected: Path,
        args: tuple[str, ...],
        *,
        timeout: int,
    ) -> CliInvocation:
        calls.append((selected, args, timeout))
        return _status_result()

    target = select_live_unity_role(
        "core-clean",
        {"UNITY_BRIDGE_CORE_CLEAN_PROJECT": str(project)},
        runner=runner,
    )

    assert target.project == project.resolve()
    assert calls == [(project.resolve(), ("status",), 15)]


def test_select_arbitrary_environment_preserves_variable_name(tmp_path: Path) -> None:
    project = _unity_project(tmp_path)

    target = select_live_unity_environment(
        "UNITY_BRIDGE_ADDRESSABLES_SUCCESS_PROJECT",
        {"UNITY_BRIDGE_ADDRESSABLES_SUCCESS_PROJECT": str(project)},
        runner=lambda *_args, **_kwargs: _status_result(),
    )

    assert target.project == project.resolve()


def test_fixture_matrix_rejects_duplicate_environment(tmp_path: Path) -> None:
    manifest = tmp_path / "matrix.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "roles": [
                    {"name": "core-clean", "environment": "UNITY_BRIDGE_DUPLICATE"},
                    {"name": "package-rich", "environment": "UNITY_BRIDGE_DUPLICATE"},
                    {
                        "name": "playback-build-target",
                        "environment": "UNITY_BRIDGE_PLAYBACK",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(LiveFixtureUnavailable, match="must be unique"):
        load_fixture_matrix(manifest)


def test_fixture_matrix_rejects_non_object_document(tmp_path: Path) -> None:
    manifest = tmp_path / "matrix.json"
    manifest.write_text("[]", encoding="utf-8")

    with pytest.raises(LiveFixtureUnavailable, match="schema_version 1 and roles"):
        load_fixture_matrix(manifest)


@pytest.mark.parametrize("value", (None, "", "true", "yes", "0"))
def test_explicit_guard_rejects_every_value_except_one(value: str | None) -> None:
    environ = {} if value is None else {"MUTATING_FIXTURE": value}

    with pytest.raises(LiveFixtureUnavailable, match="MUTATING_FIXTURE=1"):
        require_explicit_guard(environ, "MUTATING_FIXTURE", "Addressables build")


def test_explicit_guard_accepts_one() -> None:
    require_explicit_guard(
        {"MUTATING_FIXTURE": "1"},
        "MUTATING_FIXTURE",
        "Addressables build",
    )


def test_optional_adapter_probe_commands_cover_every_read_only_adapter() -> None:
    assert [(probe.name, probe.args) for probe in OPTIONAL_ADAPTER_PROBES] == [
        ("project-auditor", ("project-auditor", "availability")),
        ("code-coverage", ("coverage", "availability")),
        ("graph-toolkit", ("graph-toolkit", "availability")),
        ("entities", ("entities", "availability")),
        ("adaptive-performance", ("adaptive-performance", "availability")),
        ("multiplayer-playmode", ("multiplayer-playmode", "availability")),
        ("cinemachine", ("cinemachine", "list-cameras")),
        ("localization", ("localization", "list-locales")),
        (
            "vfx-graph",
            (
                "vfx",
                "get-info",
                "--asset-path",
                "Assets/UnityBridgeFixtures/Missing.vfx",
            ),
        ),
        (
            "timeline",
            ("timeline", "get-info", "Assets/UnityBridgeFixtures/Missing.playable"),
        ),
        ("input-system", ("input-system", "list")),
        ("addressables", ("addressables", "list-groups")),
    ]

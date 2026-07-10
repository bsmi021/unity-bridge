"""Expanded live Unity 6000.5 fixture-matrix behavior proof."""

from __future__ import annotations

import os
import time
from pathlib import Path
from uuid import uuid4

import pytest

from tests.integration.live_unity import (
    OPTIONAL_ADAPTER_PROBES,
    CliInvocation,
    FixtureRole,
    LiveFixtureUnavailable,
    LiveUnityTarget,
    OptionalAdapterProbe,
    load_fixture_matrix,
    select_live_unity_role,
)


pytestmark = pytest.mark.integration
FIXTURE_ROLES = load_fixture_matrix()
OPTIONAL_ADAPTER_TARGETS = ("core_clean_unity_65", "package_rich_unity_65")
SCENE_VIEW_STATE_KEYS = (
    "pivot_x",
    "pivot_y",
    "pivot_z",
    "rotation_x",
    "rotation_y",
    "rotation_z",
    "camera_size",
    "is_orthographic",
    "is_2d",
)
PROFILER_SLOW_MARKER = "UnityBridgeFixture.SlowMarker"
PROFILER_ALLOCATION_MARKER = "UnityBridgeFixture.AllocationMarker"


@pytest.mark.parametrize("role", FIXTURE_ROLES, ids=lambda role: role.name)
def test_required_fixture_role_is_live_or_reports_exact_skip(role: FixtureRole) -> None:
    """Each required role is independently visible in collection and skip output."""
    try:
        target = select_live_unity_role(role.name, os.environ)
    except LiveFixtureUnavailable as exc:
        pytest.skip(str(exc))

    assert target.unity_version.startswith("6000.5")
    assert target.health["healthy"] is True


@pytest.mark.parametrize("probe", OPTIONAL_ADAPTER_PROBES, ids=lambda probe: probe.name)
@pytest.mark.parametrize("target_fixture", OPTIONAL_ADAPTER_TARGETS)
def test_optional_adapter_reports_structured_availability_or_absence(
    request: pytest.FixtureRequest,
    target_fixture: str,
    probe: OptionalAdapterProbe,
) -> None:
    """Optional packages are queryable without mutation in clean and rich roles."""
    target: LiveUnityTarget = request.getfixturevalue(target_fixture)

    result = target.invoke(*probe.args, timeout=60)

    _assert_optional_adapter_outcome(probe, result)


def test_multi_angle_failure_restores_exact_scene_view_state(
    core_clean_unity_65: LiveUnityTarget,
) -> None:
    """A save failure after angle mutation must restore every Scene View field."""
    token = uuid4().hex
    unique_dir = core_clean_unity_65.project / "Temp" / "UnityBridgeFixtures" / token
    conflict = unique_dir / "blocked"
    output = f"Temp/UnityBridgeFixtures/{token}/blocked/capture.png"
    assert not unique_dir.exists()
    unique_dir.mkdir(parents=True)
    conflict.write_text("intentional directory conflict", encoding="utf-8")
    before_result = core_clean_unity_65.invoke("scene-view", "get", timeout=30)
    if before_result.returncode != 0 and "No active SceneView" in before_result.stdout:
        pytest.skip("Scene View state proof requires a non-headless Editor window.")
    before = before_result.require_success()
    try:
        result = core_clean_unity_65.invoke(
            "screenshot",
            output,
            "--multi-angle",
            "--width",
            "64",
            "--height",
            "64",
            timeout=120,
        )
        after = core_clean_unity_65.invoke("scene-view", "get", timeout=30).require_success()

        assert result.returncode != 0
        assert result.payload is not None and result.payload["success"] is False
        assert _scene_view_state(after) == _scene_view_state(before)
    finally:
        _remove_screenshot_conflict(unique_dir, conflict)


def test_profiler_known_marker_and_allocation_evidence(
    core_clean_unity_65: LiveUnityTarget,
) -> None:
    """A live Editor capture must retain known timing and allocation markers."""
    target = core_clean_unity_65
    memory = target.invoke("profiler-control", "memory", timeout=30).require_success()
    if memory.get("profiler_enabled"):
        target.invoke("profiler-control", "stop", timeout=30).require_success()
    target.invoke("profiler-frame", "clear", timeout=30).require_success()
    target.invoke(
        "profiler-control",
        "set-areas",
        "--areas",
        "CPU,Memory",
        "--allocation-callstacks",
        timeout=30,
    ).require_success()
    target.invoke("profiler-frame", "capture-start", timeout=30).require_success()
    try:
        target.invoke(
            "script",
            _profiler_fixture_expression(),
            "--return-schema",
            "scalar",
            timeout=60,
        ).require_success()
        time.sleep(0.5)
    finally:
        target.invoke("profiler-frame", "capture-stop", timeout=30).require_success()

    frame_range = target.invoke(
        "profiler-frame", "frame-range", timeout=30
    ).require_success()
    first_frame = frame_range["first_frame_index"]
    last_frame = frame_range["last_frame_index"]
    slow = target.invoke(
        "profiler-frame",
        "sample-time-summary",
        PROFILER_SLOW_MARKER,
        "--start",
        str(first_frame),
        "--end",
        str(last_frame),
        timeout=60,
    ).require_success()
    allocation = target.invoke(
        "profiler-frame",
        "sample-time-summary",
        PROFILER_ALLOCATION_MARKER,
        "--start",
        str(first_frame),
        "--end",
        str(last_frame),
        timeout=60,
    ).require_success()

    summaries = slow.get("summaries", [])
    assert len(summaries) == 1
    assert summaries[0]["marker_name"] == PROFILER_SLOW_MARKER
    assert summaries[0]["call_count"] > 0
    assert summaries[0]["total_time_ms"] > 0
    allocation_summaries = allocation.get("summaries", [])
    assert len(allocation_summaries) == 1
    assert allocation_summaries[0]["marker_name"] == PROFILER_ALLOCATION_MARKER
    assert allocation_summaries[0]["call_count"] > 0
    assert allocation_summaries[0]["gc_bytes"] > 0


def _profiler_fixture_expression() -> str:
    return (
        "new System.Func<int>(() => { "
        f'var slow = new Unity.Profiling.ProfilerMarker("{PROFILER_SLOW_MARKER}"); '
        "using (slow.Auto()) { System.Threading.Thread.SpinWait(5000000); } "
        "var allocation = new Unity.Profiling.ProfilerMarker("
        f'"{PROFILER_ALLOCATION_MARKER}"); '
        "using (allocation.Auto()) { var bytes = new byte[262144]; "
        "System.GC.KeepAlive(bytes); } return 262144; })()"
    )


def test_playmode_enter_stop_survives_domain_reload(
    playback_build_target_unity_65: LiveUnityTarget,
) -> None:
    """Enter and stop responses must remain terminal across a domain reload."""
    target = playback_build_target_unity_65
    initial = target.invoke("status", timeout=30).require_success()
    if initial.get("is_playing") or initial.get("is_playing_or_will_change_playmode"):
        pytest.skip("Playback/build-target fixture must start with the Editor stopped.")
    initial_generation = initial.get("domain_generation")
    play_dispatched = False
    try:
        play_dispatched = True
        played = target.invoke("--timeout", "90", "playmode", "play", timeout=120)
        played.require_success()
        _require_completed_operation(target, played)
        playing = _wait_for_play_state(target, expected=True)

        assert isinstance(initial_generation, int)
        assert playing["domain_generation"] > initial_generation
    finally:
        if play_dispatched:
            stopped = target.invoke("--timeout", "90", "playmode", "stop", timeout=120)
            stopped.require_success()
            _require_completed_operation(target, stopped)
    final = _wait_for_play_state(target, expected=False)
    assert final["is_playing_or_will_change_playmode"] is False


def test_addressables_build_delivers_true_success(
    addressables_success_unity_65: LiveUnityTarget,
) -> None:
    """The isolated success fixture must produce a real Addressables build."""
    data = addressables_success_unity_65.invoke(
        "--timeout", "540", "addressables", "build", timeout=600
    ).require_success()

    assert data["operation"] == "build"
    assert data["success"] is True


def test_addressables_build_delivers_true_failure(
    addressables_failure_unity_65: LiveUnityTarget,
) -> None:
    """The isolated failure fixture must return a truthful nonzero build failure."""
    result = addressables_failure_unity_65.invoke(
        "--timeout", "540", "addressables", "build", timeout=600
    )

    assert result.returncode != 0
    assert result.payload is not None and result.payload["success"] is False
    error = result.payload.get("error", "").lower()
    assert "addressables content build failed" in error
    assert "package not installed" not in error


def _assert_optional_adapter_outcome(
    probe: OptionalAdapterProbe,
    result: CliInvocation,
) -> None:
    assert isinstance(result.payload, dict)
    if result.returncode == 0:
        data = result.require_success()
        assert isinstance(data, dict)
        if probe.availability_key:
            assert isinstance(data.get(probe.availability_key), bool)
        return
    assert result.payload["success"] is False
    error = str(result.payload.get("error", "")).lower()
    assert probe.failure_fragments, f"Unexpected {probe.name} failure: {error}"
    assert any(fragment in error for fragment in probe.failure_fragments)


def _scene_view_state(data: dict[str, object]) -> dict[str, object]:
    return {key: data[key] for key in SCENE_VIEW_STATE_KEYS}


def _remove_screenshot_conflict(unique_dir: Path, conflict: Path) -> None:
    for output in unique_dir.glob("blocked/capture-*.png") if conflict.is_dir() else ():
        output.unlink(missing_ok=True)
    if conflict.is_file():
        conflict.unlink()
    elif conflict.is_dir():
        conflict.rmdir()
    unique_dir.rmdir()


def _require_completed_operation(
    target: LiveUnityTarget,
    invocation: CliInvocation,
) -> dict[str, object]:
    assert invocation.payload is not None
    command_id = invocation.payload.get("command_id")
    assert isinstance(command_id, str) and command_id
    operation = target.invoke("operation", "status", command_id, timeout=30).require_success()
    assert operation["state"] == "completed"
    assert operation["terminal_at"]
    return operation


def _wait_for_play_state(
    target: LiveUnityTarget,
    *,
    expected: bool,
    timeout: float = 20.0,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    last: dict[str, object] | None = None
    while time.monotonic() < deadline:
        result = target.invoke("status", timeout=30)
        if result.returncode == 0:
            last = result.require_success()
            transitioning = last.get("is_playing_or_will_change_playmode")
            if last.get("is_playing") is expected and not transitioning:
                return last
        time.sleep(0.2)
    raise AssertionError(f"Play mode did not become {expected}; last status: {last}")

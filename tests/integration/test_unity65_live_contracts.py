"""Live Unity 6000.5 file-protocol scenarios.

These tests require a healthy target selected through ``UNITY_BRIDGE_PROJECT``.
They exercise the supported CLI and never inspect installed handler source.
"""

from __future__ import annotations

import base64
import os
import time
from pathlib import Path
from uuid import uuid4

import pytest

from tests.integration.live_unity import LiveUnityTarget


pytestmark = pytest.mark.integration

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
MULTI_ANGLES = ("isometric", "front", "top", "right")
MODEL_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "unity65_model"
ASSEMBLY_CSHARP_EDITOR = "Assembly-CSharp-Editor"


def test_inner_failure_is_truthful_and_nonzero(live_unity_65: LiveUnityTarget) -> None:
    """A C# result with success=false must fail the outer CLI process."""
    missing = f"Assets/UnityBridgeFixtures/missing-{uuid4().hex}.asset"

    result = live_unity_65.invoke("profile", "info", missing, timeout=30)

    assert result.returncode != 0
    assert result.payload is not None
    assert result.payload["success"] is False
    assert result.payload.get("exit_code", result.returncode) != 0


def test_model_import_succeeds_then_refuses_overwrite(
    live_unity_65: LiveUnityTarget,
) -> None:
    """A unique contained model import succeeds without allowing overwrite."""
    token = uuid4().hex
    folder = f"Assets/UnityBridgeFixtures/{token}"
    destination = f"{folder}/triangle.obj"
    folder_path = live_unity_65.project / folder
    destination_path = live_unity_65.project / destination
    source = MODEL_FIXTURES / "triangle.obj"
    assert source.is_file()
    assert not folder_path.exists()
    try:
        imported = live_unity_65.invoke(
            "asset-ext",
            "import-model",
            str(source),
            destination,
            timeout=120,
        ).require_success()
        assert imported["success"] is True
        assert destination_path.is_file()
        original = destination_path.read_bytes()

        overwrite = live_unity_65.invoke(
            "asset-ext",
            "import-model",
            str(source),
            destination,
            timeout=60,
        )
        assert overwrite.returncode != 0
        assert destination_path.read_bytes() == original
    finally:
        if folder_path.exists():
            live_unity_65.invoke("asset-ext", "delete", folder, timeout=60).require_success()


def test_unsupported_model_import_rolls_back(
    core_clean_unity_65: LiveUnityTarget,
) -> None:
    """A staged glTF with no ScriptedImporter is removed after import validation."""
    token = uuid4().hex
    folder = f"Assets/UnityBridgeFixtures/{token}"
    destination = f"{folder}/triangle.gltf"
    folder_path = core_clean_unity_65.project / folder
    destination_path = core_clean_unity_65.project / destination
    source = MODEL_FIXTURES / "triangle.gltf"
    assert source.is_file()
    assert not folder_path.exists()
    try:
        result = core_clean_unity_65.invoke(
            "asset-ext",
            "import-model",
            str(source),
            destination,
            timeout=60,
        )

        assert result.returncode != 0
        assert result.payload is not None and result.payload["success"] is False
        assert "scriptedimporter" in str(result.payload.get("error", "")).lower()
        data = result.payload["data"]
        assert data["importer_type"] == "AssetImporter"
        assert data["asset"] == {
            "path": "",
            "guid": "",
            "type": "",
            "file_size": 0,
        }
        assert data["guid"] == ""
        assert not destination_path.exists()
        assert not destination_path.with_name(destination_path.name + ".meta").exists()
    finally:
        if folder_path.exists():
            core_clean_unity_65.invoke("asset-ext", "delete", folder, timeout=60).require_success()


def test_model_import_rejects_traversal_inside_fixture_root(
    live_unity_65: LiveUnityTarget,
) -> None:
    """Even traversal resolving inside the fixture root is rejected without residue."""
    token = uuid4().hex
    folder = f"Assets/UnityBridgeFixtures/{token}"
    destination = f"{folder}/Sub/../triangle.obj"
    folder_path = live_unity_65.project / folder
    canonical_destination = folder_path / "triangle.obj"
    source = MODEL_FIXTURES / "triangle.obj"
    assert source.is_file()
    assert not folder_path.exists()
    try:
        result = live_unity_65.invoke(
            "asset-ext",
            "import-model",
            str(source),
            destination,
            timeout=60,
        )

        assert result.returncode != 0
        assert result.payload is not None and result.payload["success"] is False
        assert not canonical_destination.exists()
    finally:
        if folder_path.exists():
            live_unity_65.invoke("asset-ext", "delete", folder, timeout=60).require_success()


def test_menu_validation_never_executes_play_menu(
    live_unity_65: LiveUnityTarget,
) -> None:
    """Validation of an enabled menu item must not execute or enter play mode."""
    initial = live_unity_65.invoke("status", timeout=15).require_success()
    if initial.get("is_playing") or initial.get("is_playing_or_will_change_playmode"):
        pytest.skip("Menu validation fixture requires the Editor to be stopped.")
    observations: list[dict[str, object]] = []
    try:
        validated = live_unity_65.invoke(
            "menu",
            "Edit/Play",
            "--validate-only",
            timeout=30,
        ).require_success()
        if validated.get("is_enabled") is not True:
            validated = live_unity_65.invoke(
                "menu",
                "Assets/Refresh",
                "--validate-only",
                timeout=30,
            ).require_success()
        assert validated.get("is_enabled") is True
        assert validated.get("executed") is False

        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            status = live_unity_65.invoke("status", timeout=15).require_success()
            observations.append(status)
            time.sleep(0.2)

        assert observations
        assert all(not item.get("is_playing") for item in observations)
        assert all(not item.get("is_playing_or_will_change_playmode") for item in observations)
    finally:
        if any(item.get("is_playing") for item in observations):
            live_unity_65.invoke("playmode", "stop", timeout=90).require_success()


def test_screenshot_camera_selection_returns_base64_png(
    live_unity_65: LiveUnityTarget,
) -> None:
    """A named fixture camera must be selected and returned as inline PNG data."""
    token = uuid4().hex
    configured_camera = os.environ.get("UNITY_BRIDGE_FIXTURE_CAMERA_PATH", "").strip()
    camera_path = configured_camera or f"UnityBridgeFixtureCamera-{token}"
    created_camera = not configured_camera
    camera_output = f"Temp/UnityBridgeFixtures/{token}-camera.png"
    output_path = live_unity_65.project / camera_output
    assert not output_path.exists()

    try:
        if created_camera:
            live_unity_65.invoke(
                "hierarchy",
                "create-primitive",
                "camera",
                "--name",
                camera_path,
                timeout=30,
            ).require_success()
        data = live_unity_65.invoke(
            "screenshot",
            camera_output,
            "--camera",
            camera_path,
            "--width",
            "64",
            "--height",
            "64",
            "--inline-base64",
            timeout=60,
        ).require_success()
        assert camera_path in data["message"]
        assert base64.b64decode(data["base64_png"]).startswith(b"\x89PNG\r\n\x1a\n")
    finally:
        output_path.unlink(missing_ok=True)
        if created_camera:
            live_unity_65.invoke("undo", "perform", timeout=30).require_success()


def test_screenshot_multi_angle_restores_exact_scene_view_state(
    live_unity_65: LiveUnityTarget,
) -> None:
    """Multi-angle capture must return four PNGs and restore full camera state."""
    token = uuid4().hex
    multi_output = f"Temp/UnityBridgeFixtures/{token}-multi.png"
    output_paths = [
        live_unity_65.project / f"Temp/UnityBridgeFixtures/{token}-multi-{angle}.png"
        for angle in MULTI_ANGLES
    ]
    assert all(not path.exists() for path in output_paths)
    before_result = live_unity_65.invoke("scene-view", "get", timeout=30)
    if before_result.returncode != 0 and "No active SceneView" in before_result.stdout:
        pytest.skip("Scene View state proof requires a non-headless Editor window.")
    before = before_result.require_success()
    try:
        data = live_unity_65.invoke(
            "screenshot",
            multi_output,
            "--width",
            "64",
            "--height",
            "64",
            "--inline-base64",
            "--multi-angle",
            timeout=120,
        ).require_success()
        captures = data["captures"]
        assert [capture["angle"] for capture in captures] == list(MULTI_ANGLES)
        for capture in captures:
            assert base64.b64decode(capture["base64_png"]).startswith(b"\x89PNG\r\n\x1a\n")

        after = live_unity_65.invoke("scene-view", "get", timeout=30).require_success()
        assert {key: after[key] for key in SCENE_VIEW_STATE_KEYS} == {
            key: before[key] for key in SCENE_VIEW_STATE_KEYS
        }
    finally:
        for path in output_paths:
            path.unlink(missing_ok=True)


def test_build_profile_create_waits_for_terminal_callback(
    live_unity_65: LiveUnityTarget,
) -> None:
    """Create must return only after Unity's callback provides an asset path."""
    discovered = live_unity_65.invoke("profile", "platforms", timeout=30).require_success()
    platforms = discovered.get("platforms", [])
    assert platforms, "Build Profile callback proof requires an installed platform module."
    platform_id = platforms[0]["platform_id"]
    profile_name = f"UnityBridgeFixture-{uuid4().hex}"
    profile_path: str | None = None
    try:
        created = live_unity_65.invoke(
            "--timeout",
            "120",
            "profile",
            "create",
            profile_name,
            "--platform-id",
            platform_id,
            timeout=120,
        ).require_success()
        profile_path = created.get("profile_path")

        assert created["operation"] == "create"
        assert created["success"] is True
        assert isinstance(profile_path, str) and profile_path.startswith("Assets/")
        info = live_unity_65.invoke("profile", "info", profile_path, timeout=30).require_success()
        assert info["success"] is True
    finally:
        if profile_path:
            live_unity_65.invoke("asset-ext", "delete", profile_path, timeout=60).require_success()


def test_build_profile_create_delivers_terminal_failure(
    live_unity_65: LiveUnityTarget,
) -> None:
    """An unknown but well-formed platform GUID must terminate as a failure."""
    profile_name = f"UnityBridgeInvalidFixture-{uuid4().hex}"
    unknown_platform_id = uuid4().hex

    result = live_unity_65.invoke(
        "profile",
        "create",
        profile_name,
        "--platform-id",
        unknown_platform_id,
        timeout=120,
    )

    assert result.returncode != 0
    assert result.payload is not None
    assert result.payload["success"] is False


def test_profiler_capture_honors_frame_budget(live_unity_65: LiveUnityTarget) -> None:
    """A two-frame capture budget must automatically disable the profiler."""
    prior = live_unity_65.invoke("profiler-control", "memory", timeout=30).require_success()
    if prior.get("profiler_enabled"):
        live_unity_65.invoke("profiler-control", "stop", timeout=30).require_success()
    try:
        cleared = live_unity_65.invoke(
            "profiler-frame", "clear", timeout=30
        ).require_success()
        assert cleared["last_frame_index"] == -1
        started = live_unity_65.invoke(
            "profiler-frame",
            "capture-start",
            "--frame-count",
            "2",
            timeout=30,
        ).require_success()
        assert "2-frame budget" in started["message"]
        initial_last_frame = started["last_frame_index"]

        deadline = time.monotonic() + 10.0
        final_memory: dict[str, object] | None = None
        while time.monotonic() < deadline:
            final_memory = live_unity_65.invoke(
                "profiler-control", "memory", timeout=30
            ).require_success()
            if final_memory.get("profiler_enabled") is False:
                break
            time.sleep(0.2)

        assert final_memory is not None
        frame_range = live_unity_65.invoke(
            "profiler-frame", "frame-range", timeout=30
        ).require_success()
        assert final_memory["profiler_enabled"] is False
        frames_captured = frame_range["last_frame_index"] - initial_last_frame
        assert frames_captured >= 2
        assert frame_range["requested_frame_count"] == 2
        assert frame_range["start_frame_index"] == initial_last_frame
        assert frame_range["target_frame_index"] == initial_last_frame + 2
        assert (
            frame_range["stop_observed_frame_index"]
            >= frame_range["target_frame_index"]
        )
        assert (
            frame_range["stop_observed_frame_index"]
            <= frame_range["last_frame_index"]
        )
        assert frame_range["actual_frame_count"] == frames_captured
        assert frame_range["overshoot_frames"] == frames_captured - 2
        assert frame_range["runtime_profiler_enabled"] is False
        assert frame_range["editor_driver_enabled"] is False
        assert frame_range["profile_editor"] is True
        assert frame_range["capture_owner"] == "profiler-frame"
    finally:
        live_unity_65.invoke("profiler-control", "stop", timeout=30).require_success()


def test_profiler_control_stop_cancels_frame_budget(
    live_unity_65: LiveUnityTarget,
) -> None:
    """Stopping through profiler-control must terminate profiler-frame state."""
    target = live_unity_65
    prior = target.invoke("profiler-control", "memory", timeout=30).require_success()
    if prior.get("profiler_enabled"):
        target.invoke("profiler-control", "stop", timeout=30).require_success()
    target.invoke("profiler-frame", "clear", timeout=30).require_success()
    started = target.invoke(
        "profiler-frame",
        "capture-start",
        "--frame-count",
        "1000",
        timeout=30,
    ).require_success()
    assert started["requested_frame_count"] == 1000
    try:
        target.invoke("profiler-control", "stop", timeout=30).require_success()
        stopped = target.invoke(
            "profiler-frame", "frame-range", timeout=30
        ).require_success()

        assert stopped["editor_driver_enabled"] is False
        assert stopped["runtime_profiler_enabled"] is False
        assert stopped["stop_observed_frame_index"] >= 0
        assert stopped["stop_observed_frame_index"] >= stopped["start_frame_index"]
        assert stopped["frame_budget_armed"] is False
    finally:
        target.invoke("profiler-frame", "capture-stop", timeout=30).require_success()


def test_generic_linq_probe_has_no_duplicate_core_references(
    live_unity_65: LiveUnityTarget,
) -> None:
    """The generic host must compile LINQ without duplicate core-type ambiguity."""
    data = live_unity_65.invoke(
        "script",
        "System.Linq.Enumerable.Range(1, 3).Sum()",
        "--return-schema",
        "scalar",
        timeout=30,
    ).require_success()

    assert data["value"]["kind"] == "integer"
    assert data["value"]["string_value"] == "6"
    assert data["compiler_diagnostics"] == []


def test_exact_assembly_identity_replays_the_selected_project_assembly(
    live_unity_65: LiveUnityTarget,
) -> None:
    """A discovered full name, MVID, and path must resolve to that exact assembly."""
    discovered = live_unity_65.invoke("script", "42", timeout=30).require_success()
    identity = next(
        item for item in discovered["resolved_assemblies"] if item["name"] == ASSEMBLY_CSHARP_EDITOR
    )
    selector = "|".join((identity["full_name"], identity["mvid"], identity["path"]))

    data = live_unity_65.invoke(
        "script",
        "typeof(BWS.Editor.ClaudeCodeBridge.IExecuteScriptJob).Name",
        "--assembly-identity",
        selector,
        "--return-schema",
        "scalar",
        timeout=30,
    ).require_success()

    assert data["value"]["string_value"] == "IExecuteScriptJob"
    assert any(
        item["full_name"] == identity["full_name"]
        and item["mvid"] == identity["mvid"]
        and item["path"] == identity["path"]
        for item in data["resolved_assemblies"]
    )


def test_cooperative_job_completes_across_editor_updates(
    live_unity_65: LiveUnityTarget,
) -> None:
    """An indexed job must advance one bounded step per Editor update."""
    expression = (
        "new DelegateExecuteScriptJob(stepIndex => stepIndex < 2 "
        "? ExecuteScriptJobStep.Continue() "
        ": ExecuteScriptJobStep.Complete(stepIndex))"
    )

    data = live_unity_65.invoke(
        "script-job", expression, "--return-schema", "scalar", timeout=30
    ).require_success()

    assert data["value"]["kind"] == "integer"
    assert data["value"]["string_value"] == "2"
    assert data["message"] == "Cooperative job completed."


def test_cooperative_job_deadline_is_terminal(live_unity_65: LiveUnityTarget) -> None:
    """An unfinished cooperative job must fail at its Unity-side deadline."""
    expression = "new DelegateExecuteScriptJob(stepIndex => ExecuteScriptJobStep.Continue())"

    result = live_unity_65.invoke("script-job", expression, "--timeout", "1", timeout=15)

    assert result.returncode != 0
    assert result.payload is not None
    assert result.payload["success"] is False
    assert result.payload["error"] == "Job deadline exceeded."
    assert result.payload["data"]["message"] == "Job deadline exceeded."


def test_detached_cooperative_job_can_be_cancelled(
    live_unity_65: LiveUnityTarget,
) -> None:
    """Cancellation must be accepted while running and persist a terminal failure."""
    expression = "new DelegateExecuteScriptJob(stepIndex => ExecuteScriptJobStep.Continue())"
    queued = live_unity_65.invoke(
        "script-job", expression, "--timeout", "30", "--detach", timeout=15
    ).require_success()
    command_id = queued["command_id"]
    terminal_observed = False
    try:
        running = live_unity_65.invoke(
            "operation",
            "wait",
            command_id,
            "--timeout",
            "1",
            "--poll-interval",
            "0.1",
        ).require_success()
        assert running["status"] == "running"
        assert running["operation"]["state"] == "running"

        cancelled = live_unity_65.invoke("script-cancel", command_id, timeout=15).require_success()
        assert cancelled["accepted"] is True
        assert cancelled["target_state"] == "cancellation-requested"

        terminal = live_unity_65.invoke(
            "operation",
            "wait",
            command_id,
            "--timeout",
            "10",
            "--poll-interval",
            "0.1",
        )
        terminal_observed = True
        assert terminal.returncode != 0
        assert terminal.payload is not None
        assert terminal.payload["error"] == "Job cancellation requested."
    finally:
        if not terminal_observed:
            live_unity_65.invoke("script-cancel", command_id, timeout=15)
            live_unity_65.invoke(
                "operation",
                "wait",
                command_id,
                "--timeout",
                "10",
                "--poll-interval",
                "0.1",
            )


def test_declared_file_mutation_rolls_back_on_job_failure(
    live_unity_65: LiveUnityTarget,
) -> None:
    """A declared new asset file must be reported and removed after job failure."""
    leaf = f"UnityBridgeRollback-{uuid4().hex}.txt"
    asset_path = f"Assets/{leaf}"
    physical_path = live_unity_65.project / asset_path
    expression = (
        "new DelegateExecuteScriptJob(stepIndex => { "
        f'System.IO.File.WriteAllText(System.IO.Path.Combine(UnityEngine.Application.dataPath, "{leaf}"), "temporary"); '
        'return ExecuteScriptJobStep.Fail("rollback probe"); })'
    )
    try:
        result = live_unity_65.invoke(
            "script-job",
            expression,
            "--intent",
            "mutating",
            "--asset-path",
            asset_path,
            "--undo-label",
            "Unity Bridge rollback probe",
            "--timeout",
            "30",
            timeout=45,
        )

        assert result.returncode != 0
        assert result.payload is not None
        mutation = result.payload["data"]["mutation"]
        assert mutation["governed"] is True
        assert mutation["reverted"] is True
        assert asset_path in mutation["declared_file_paths"]
        assert not physical_path.exists()
    finally:
        physical_path.unlink(missing_ok=True)
        Path(f"{physical_path}.meta").unlink(missing_ok=True)


def test_cooperative_job_domain_reload_is_terminal(
    reload_probe_unity_65: LiveUnityTarget,
) -> None:
    """An explicitly authorized compilation reload must persist interruption truth."""
    expression = (
        "new DelegateExecuteScriptJob(stepIndex => { "
        "if (stepIndex == 1) "
        "UnityEditor.Compilation.CompilationPipeline.RequestScriptCompilation(); "
        "return ExecuteScriptJobStep.Continue(); })"
    )

    result = reload_probe_unity_65.invoke("script-job", expression, "--timeout", "30", timeout=90)

    assert result.returncode != 0
    assert result.payload is not None
    assert result.payload["error"] == (
        "Command interrupted by Unity domain reload before final response."
    )
    command_id = result.payload["command_id"]
    operation = reload_probe_unity_65.invoke(
        "operation", "status", command_id, timeout=15
    ).require_success()
    assert operation["state"] == "interrupted"
    assert operation["terminal_at"]

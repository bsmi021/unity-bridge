"""Behavioral smoke coverage for deterministic CLI dispatch wrappers."""

from __future__ import annotations

import hashlib
import importlib
import inspect
import json
import pkgutil
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from unity_bridge import commands
from unity_bridge.core.bridge import CommandResult
from unity_bridge.core.output import OutputFormatter


EXCLUDED_CLI_WRAPPERS = {
    ("code_coverage", "_recording_cli"),
    ("console", "console_watch_cli"),
    ("diagnostics", "doctor_cli"),
    ("diagnostics", "status_cli"),
    ("lifecycle", "clean_cli"),
    ("lifecycle", "init_cli"),
    ("lifecycle", "install_cli"),
    ("lifecycle", "version_cli"),
    ("material", "material_cli"),
    ("operation", "operation_list_cli"),
    ("operation", "operation_submit_cli"),
    ("operation", "operation_status_cli"),
    ("operation", "operation_wait_cli"),
    ("serve", "serve_cli"),
    ("testing", "test_events_cli"),
    ("testing", "test_failures_cli"),
    ("testing", "test_history_cli"),
    ("testing", "test_preflight_cli"),
    ("testing", "test_progress_cli"),
    ("testing", "test_rerun_failed_cli"),
    ("testing", "test_results_cli"),
    ("workflow", "tdd_cli"),
    ("workflow", "test_watch_cli"),
}


LOCAL_RESULT_WRAPPERS = {
    ("workflow", "snapshot_diff_cli"),
}


CUSTOM_KWARGS: dict[tuple[str, str], dict[str, Any] | str] = {
    ("animator", "animator_cli"): {
        "action": "get-state",
        "object_path": "Player",
    },
    ("animation", "animation_set_curve_cli"): {
        "clip_path": "Assets/Walk.anim",
        "property_name": "m_LocalPosition.y",
        "keyframes_json": '[{"time":0,"value":0}]',
    },
    ("asset", "asset_cli"): {
        "action": "find",
        "path": "Assets",
        "asset_type": "Material",
        "pattern": "Mat*",
    },
    ("asset_extended", "asset_create_cli"): {
        "path": "Assets/New.asset",
        "asset_type": "ScriptableObject",
    },
    ("asset_extended", "asset_export_cli"): {
        "output": "Build/out.unitypackage",
        "paths": ["Assets/A.asset"],
        "include_deps": True,
    },
    ("asset_extended", "asset_reserialize_cli"): {
        "paths": ["Assets/A.asset"],
        "mode": "both",
    },
    ("batch", "batch_cli"): "batch_file",
    ("build", "build_cli"): {
        "target": "StandaloneWindows64",
        "validate_only": True,
        "output": "Build/Game",
        "dev": True,
        "auto_run": True,
        "profiler_opt": True,
        "compress": "lz4",
        "scenes": "Assets/A.unity,Assets/B.unity",
        "subtarget": "Player",
        "timeout": 600,
    },
    ("component_ext", "component_paste_cli"): {
        "object_path": "Player",
        "component_type": "Transform",
        "data": "{}",
    },
    ("diagnostics", "profiler_cli"): {
        "memory": True,
        "rendering": True,
        "cpu": True,
    },
    ("environment_settings", "environment_set_cli"): {
        "fog_flag": True,
        "fog_color": "1,1,1",
        "fog_density": 0.2,
        "ambient_intensity": 1.0,
        "skybox": "none",
    },
    ("graphics_settings", "graphics_set_cli"): {
        "render_pipeline": "Assets/Pipeline.asset",
        "srp_batching": True,
        "log_shader": True,
    },
    ("hierarchy", "component_set_cli"): {
        "object_path": "Player",
        "component_type": "Transform",
        "update": ["position.x:1"],
    },
    ("import_settings", "import_settings_set_cli"): {
        "path": "Assets/Texture.png",
        "setting": ["maxTextureSize:512"],
    },
    ("import_settings", "import_settings_bulk_set_cli"): {
        "folder": "Assets/Textures",
        "setting": ["maxTextureSize:512"],
        "filter_pattern": "*.png",
    },
    ("material", "modify_cli"): {
        "path": "Assets/M.mat",
        "properties": '{"_Color":{"r":1}}',
    },
    ("physics2d", "set_cli"): {
        "gravity": "0,-9.81",
        "velocity_iterations": 8,
        "position_iterations": 3,
        "velocity_threshold": 1.0,
        "default_contact_offset": 0.01,
        "queries_hit_triggers": True,
        "auto_sync_transforms": False,
    },
    ("physics_config", "physics_set_cli"): {
        "gravity": "0,-9.81,0",
        "solver_iterations": 6,
    },
    ("playmode", "playmode_cli"): {
        "action": "play",
    },
    ("project_auditor", "run_cli"): {
        "output_path": "artifacts/project-auditor.json",
        "max_issues": 100,
        "categories": "Performance,Code",
        "assembly_names": "Assembly-CSharp",
        "platform": "StandaloneWindows64",
    },
    ("scripting", "script_cli"): {
        "expression": "Debug.Log(1);",
        "file": None,
        "intent": "read-only",
        "assembly": [],
        "assembly_identity": [],
        "object_id": [],
        "asset_path": [],
        "undo_label": None,
        "return_schema": "auto",
        "allow_internal_reflection": False,
        "timeout": 30,
    },
    ("scripting_assembly_probe", "script_probe_assemblies_cli"): "assembly_snapshot_file",
    ("scripting_job_cli", "script_job_cli"): {
        "expression": "new TestJob()",
        "file": None,
        "intent": "read-only",
        "assembly": [],
        "assembly_identity": [],
        "object_id": [],
        "asset_path": [],
        "undo_label": None,
        "return_schema": "auto",
        "allow_internal_reflection": False,
        "timeout": 30,
        "detach": False,
    },
    ("select", "select_cli"): {
        "objects": ["Player"],
        "clear": False,
    },
    ("terrain", "terrain_create_cli"): {
        "name": "TestTerrain",
        "size": "100,20,100",
    },
    ("terrain", "terrain_set_heights_cli"): {
        "heights_json": "[[0.1,0.2],[0.3,0.4]]",
        "x": 0,
        "y": 0,
        "terrain_name": "TestTerrain",
    },
    ("transform", "transform_set_cli"): {
        "object_path": "Player",
        "position": "1,2,3",
        "rotation": "0,90,0",
        "scale": "1,1,1",
        "local": True,
    },
    ("workflow", "snapshot_diff_cli"): "snapshot_diff_files",
    ("workflow", "snapshot_save_cli"): "snapshot_file",
}


def _cli_cases() -> list[pytest.ParamSpec]:
    cases = []
    for module_info in pkgutil.iter_modules(commands.__path__):
        if module_info.ispkg:
            continue
        module = importlib.import_module(f"unity_bridge.commands.{module_info.name}")
        for name, obj in vars(module).items():
            if inspect.isfunction(obj) and name.endswith("_cli"):
                key = (module_info.name, name)
                if key not in EXCLUDED_CLI_WRAPPERS:
                    cases.append(pytest.param(*key, id=f"{key[0]}::{key[1]}"))
    return cases


@pytest.mark.parametrize(("module_name", "function_name"), _cli_cases())
def test_cli_wrapper_dispatches_with_fake_bridge(
    module_name: str,
    function_name: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = importlib.import_module(f"unity_bridge.commands.{module_name}")
    wrapper = getattr(module, function_name)
    state, bridge = _state(tmp_path)
    ctx = SimpleNamespace(obj=state, invoked_subcommand=None)
    kwargs = _kwargs_for(module_name, function_name, wrapper, tmp_path)
    if (module_name, function_name) == (
        "scripting_assembly_probe",
        "script_probe_assemblies_cli",
    ):
        _configure_assembly_probe_bridge(bridge, tmp_path)

    wrapper(ctx, **kwargs)

    capsys.readouterr()
    if (module_name, function_name) in LOCAL_RESULT_WRAPPERS:
        assert not bridge.send_command.called
        assert not bridge.send_command_with_retry.called
        return

    assert bridge.send_command.called or bridge.send_command_with_retry.called
    call = (
        bridge.send_command_with_retry.call_args
        if bridge.send_command_with_retry.called
        else bridge.send_command.call_args
    )
    command_type, parameters = _bridge_call_payload(call)
    assert isinstance(command_type, str) and command_type
    assert isinstance(parameters, dict)


def _state(tmp_path: Path) -> tuple[SimpleNamespace, MagicMock]:
    bridge = MagicMock()
    result = CommandResult(
        success=True,
        data={"ok": True},
        command_id="cmd-1",
        execution_time_ms=1,
    )
    bridge.project_root = tmp_path
    bridge.send_command = AsyncMock(return_value=result)
    bridge.send_command_with_retry = AsyncMock(return_value=result)
    state = SimpleNamespace(
        bridge=bridge,
        formatter=OutputFormatter(),
        project_root=tmp_path,
    )
    return state, bridge


def _kwargs_for(
    module_name: str,
    function_name: str,
    wrapper: Any,
    tmp_path: Path,
) -> dict[str, Any]:
    custom = CUSTOM_KWARGS.get((module_name, function_name))
    if custom == "batch_file":
        batch = tmp_path / "batch.json"
        batch.write_text(
            json.dumps({"commands": [{"type": "query-hierarchy", "parameters": {}}]}),
            encoding="utf-8",
        )
        return {"file": batch, "stop_on_error": True, "parallel": True}
    if custom == "assembly_snapshot_file":
        assembly_path = tmp_path / "UnityEditor.CoreModule.dll"
        assembly_path.write_bytes(b"runtime-module")
        snapshot = tmp_path / "unity-api-snapshot.jsonl"
        snapshot.write_text(
            json.dumps(
                {
                    "context": {"unity": {"version": "6000.5.1f1"}},
                    "assembly": {
                        "name": "UnityEditor.CoreModule",
                        "path": assembly_path.as_posix(),
                        "mvid": "11111111-1111-1111-1111-111111111111",
                        "sha256": hashlib.sha256(assembly_path.read_bytes()).hexdigest(),
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return {"snapshot": snapshot, "output": None, "timeout": 30}
    if custom == "snapshot_diff_files":
        first = tmp_path / "before.json"
        second = tmp_path / "after.json"
        first.write_text(json.dumps({"hierarchy": {"children": []}}), encoding="utf-8")
        second.write_text(json.dumps({"hierarchy": {"children": []}}), encoding="utf-8")
        return {"file1": first, "file2": second}
    if custom == "snapshot_file":
        return {"file": tmp_path / "snapshot.json", "depth": 2, "max_objects": 10, "root": "Player"}
    kwargs = dict(custom) if isinstance(custom, dict) else {}
    for name, parameter in inspect.signature(wrapper).parameters.items():
        if name == "ctx" or name in kwargs:
            continue
        kwargs[name] = _sample_parameter_value(name, parameter)
    return kwargs


def _configure_assembly_probe_bridge(bridge: MagicMock, tmp_path: Path) -> None:
    identity = {
        "kind": "dto",
        "fields": [
            _dto_string("name", "UnityEditor.CoreModule"),
            _dto_string(
                "fullName",
                "UnityEditor.CoreModule, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null",
            ),
            _dto_string("mvid", "11111111-1111-1111-1111-111111111111"),
            _dto_string("path", str(tmp_path / "UnityEditor.CoreModule.dll")),
        ],
    }
    listed = CommandResult(
        success=True,
        data={"value": {"kind": "collection", "items": [identity]}},
    )
    compiled = CommandResult(success=True, data={"value": {"kind": "scalar"}})
    bridge.send_command_with_retry = AsyncMock(side_effect=[listed, compiled])


def _dto_string(name: str, value: str) -> dict[str, object]:
    return {
        "name": name,
        "value": {"kind": "scalar", "string_value": value},
    }


def _sample_parameter_value(name: str, parameter: inspect.Parameter) -> Any:
    if parameter.default is inspect.Parameter.empty or parameter.default is None:
        return _required_sample_value(name)
    if isinstance(parameter.default, bool):
        if name == "detach":
            return parameter.default
        return not parameter.default if name != "clear" else parameter.default
    return parameter.default


def _required_sample_value(name: str) -> Any:
    if name in {"object_path", "game_object_path", "tilemap_path", "terrain_name"}:
        return "Player"
    if "component_type" in name:
        return "Transform"
    if name in {"position", "rotation", "pivot", "grid_size", "move_snap", "fog_color"}:
        return "1,2,3"
    if name in {"size", "scale"}:
        return "1,1,1"
    if name in {"gravity"}:
        return "0,-9.81,0"
    if name in {"json_data", "data"}:
        return "{}"
    if name in {
        "paths",
        "objects",
        "devices",
        "test_names",
        "group_names",
        "categories",
        "assemblies",
    }:
        return ["Name"]
    if name in {"width", "height", "x", "y", "z", "index", "order", "layer", "limit"}:
        return 1
    if name.startswith("max_") or name in {"timeout", "depth", "group_index", "min_tests"}:
        return 1
    if name in {"frame_rate", "volume", "fog_density", "ambient_intensity", "poll_interval"}:
        return 1.0
    if name.endswith("_path") or name in {"path", "source", "dest", "package", "input_val"}:
        return "Assets/Test.asset"
    if name in {"file", "file1", "file2"}:
        return Path("unused.json")
    return "Name"


def _bridge_call_payload(call_args: Any) -> tuple[str, dict[str, Any]]:
    if "command_type" in call_args.kwargs:
        return call_args.kwargs["command_type"], call_args.kwargs["parameters"]
    return call_args.args[0], call_args.args[1]

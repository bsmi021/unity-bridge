"""Regression tests for Unity save-dialog modal prevention."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock


ROOT = Path(__file__).resolve().parents[2]
BRIDGE_DIR = ROOT / "ClaudeCodeBridge"


class TestModalRecoverySource:
    async def test_scene_load_sends_csharp_save_current_scene_contract(
        self, mock_bridge: MagicMock
    ) -> None:
        # Arrange
        from unity_bridge.commands.scene import scene_load

        # Act
        await scene_load(mock_bridge, "Assets/Scenes/Main.unity", save_current=False)

        # Assert
        params = _extract_parameters(mock_bridge.send_command_with_retry.call_args)
        assert params["saveCurrentScene"] is False
        assert "saveCurrent" not in params

    def test_csharp_scene_params_do_not_implicitly_save_current_scene(self) -> None:
        # Arrange
        source = _read_bridge_source("BridgeModels.cs")

        # Act / Assert
        assert "public bool saveCurrentScene = true" not in source
        assert "public bool saveCurrentScene;" in source

    def test_run_tests_preflights_scene_state_before_unity_test_runner(self) -> None:
        # Arrange
        source = _read_bridge_source("RunTestsCommandHandler.cs")
        marker = 'BridgeSceneModalRecovery.PrepareForAutomation("run-tests"'

        # Act / Assert
        assert marker in source
        assert source.index(marker) < source.index("BridgeTestRunReporter.BeginRunAndExecute")
        assert "return BridgeResponse.Error(command.commandId, command.commandType" in source

    def test_test_reporter_discards_blank_test_scenes_after_run_finished(self) -> None:
        # Arrange
        source = _read_bridge_source("BridgeTestRunReporter.cs")
        marker = 'BridgeSceneModalRecovery.DiscardUnsavedBlankScenes("run-tests-finished")'

        # Act / Assert
        assert marker in source
        assert source.index(marker) < source.index("Clear();")

    def test_scene_operations_prepare_before_single_scene_replacement(self) -> None:
        # Arrange
        source = _read_bridge_source("SceneOperationCommandHandler.cs")
        load_save_marker = (
            'BridgeSceneModalRecovery.PrepareForExplicitSave("scene-operation load save-current"'
        )
        create_save_marker = (
            'BridgeSceneModalRecovery.PrepareForExplicitSave("scene-operation create save-current"'
        )
        load_marker = 'BridgeSceneModalRecovery.PrepareForAutomation("scene-operation load"'
        create_marker = 'BridgeSceneModalRecovery.PrepareForAutomation("scene-operation create"'

        # Act / Assert
        assert load_save_marker in source
        assert create_save_marker in source
        assert source.index(load_save_marker) < source.index("EditorSceneManager.SaveScene")
        assert source.index(create_save_marker) < source.rindex("EditorSceneManager.SaveScene")
        assert load_marker in source
        assert create_marker in source
        assert source.index(load_marker) < source.index("EditorSceneManager.OpenScene")
        assert source.index(create_marker) < source.index("EditorSceneManager.NewScene")

    def test_scene_setup_restore_prepares_before_restore_scene_manager_setup(self) -> None:
        # Arrange
        source = _read_bridge_source("SceneSetupCommandHandler.cs")
        marker = 'BridgeSceneModalRecovery.PrepareForAutomation("scene-setup restore"'

        # Act / Assert
        assert marker in source
        assert source.index(marker) < source.index("EditorSceneManager.RestoreSceneManagerSetup")

    def test_playmode_target_scene_prepares_before_opening_scene(self) -> None:
        # Arrange
        source = _read_bridge_source("PlayModeControlCommandHandler.cs")
        marker = 'BridgeSceneModalRecovery.PrepareForAutomation("playmode-control play"'

        # Act / Assert
        assert marker in source
        assert source.index(marker) < source.index("EditorSceneManager.OpenScene")

    def test_modal_recovery_helper_only_discards_blank_untitled_scenes(self) -> None:
        # Arrange
        source_path = BRIDGE_DIR / "BridgeSceneModalRecovery.cs"

        # Act / Assert
        assert source_path.is_file()
        source = source_path.read_text(encoding="utf-8")
        assert "string.IsNullOrEmpty(scene.path)" in source
        assert "scene.GetRootGameObjects()" in source
        assert "EditorUtility.IsDirty(root)" in source
        assert "root.GetComponents<Component>()" in source
        assert '"Main Camera"' in source
        assert '"Directional Light"' in source
        assert "EditorSceneManager.CloseScene(scene, true)" in source
        assert "Refusing to trigger Unity save modal" in source
        assert "if (!TryDiscardUnsavedBlankScenes(context, out message))" in source

    def test_modal_recovery_never_discards_dirty_untitled_scenes(self) -> None:
        # Arrange
        source = _read_bridge_source("BridgeSceneModalRecovery.cs")

        # Act / Assert
        assert "if (!scene.IsValid() || !scene.isLoaded || scene.isDirty" in source

    def test_legacy_editor_scene_cleanup_api_forwards_to_modal_recovery(self) -> None:
        # Arrange
        source_path = BRIDGE_DIR / "BridgeEditorSceneCleanup.cs"

        # Act / Assert
        assert source_path.is_file()
        source = source_path.read_text(encoding="utf-8")
        assert "public static class BridgeEditorSceneCleanup" in source
        assert "BridgeSceneModalRecovery.PrepareForAutomation(context, out message)" in source
        assert "BridgeSceneModalRecovery.PrepareForExplicitSave(context, out message)" in source
        assert "BridgeSceneModalRecovery.DiscardUnsavedBlankScenes(context)" in source


def _read_bridge_source(file_name: str) -> str:
    return (BRIDGE_DIR / file_name).read_text(encoding="utf-8")


def _extract_parameters(call_args: Any) -> dict:
    if call_args.kwargs.get("parameters") is not None:
        return call_args.kwargs["parameters"]
    if len(call_args.args) >= 2:
        return call_args.args[1]
    return {}

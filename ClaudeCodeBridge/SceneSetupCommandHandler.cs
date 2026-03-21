using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for extended scene management operations.
    ///
    /// PURPOSE:
    /// Provides Claude Code with multi-scene editing, scene setup save/restore,
    /// play mode start scene control, cross-scene reference detection,
    /// and preview scene management.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "save"           - Save current multi-scene layout
    /// 2. "restore"        - Restore a previously saved layout
    /// 3. "list"           - List all saved scene setups
    /// 4. "play-start"     - Get/set/clear play mode start scene
    /// 5. "cross-refs"     - Detect cross-scene references
    /// 6. "list-loaded"    - List all loaded scenes with status
    /// 7. "preview-create" - Create an empty preview scene
    /// 8. "preview-close"  - Close a preview scene by handle
    ///
    /// Scene setups are stored in .claude/unity/scene-setups/.
    /// </summary>
    public class SceneSetupCommandHandler : ICommandHandler
    {
        public string CommandType => "scene-setup-operation";

        private static readonly string PROJECT_ROOT =
            Directory.GetParent(Application.dataPath).FullName;
        private static readonly string SETUPS_PATH =
            Path.Combine(PROJECT_ROOT, ".claude", "unity", "scene-setups");

        private static readonly Regex VALID_NAME_REGEX =
            new Regex(@"^[a-zA-Z0-9_-]{1,64}$", RegexOptions.Compiled);

        // Track preview scenes by sequential handle
        private static int _nextPreviewHandle = 1;
        private static readonly Dictionary<int, Scene> _previewScenes =
            new Dictionary<int, Scene>();

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(
                        command.commandId,
                        command.commandType,
                        "Cannot perform scene setup operations while scripts are compiling.");
                }

                var parameters = JsonUtility.FromJson<SceneSetupParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new SceneSetupParams();

                BridgeLogger.LogDebug($"Executing scene setup operation: {parameters.operation}");

                switch (parameters.operation?.ToLower())
                {
                    case "save":
                        return ExecuteSave(command, parameters);
                    case "restore":
                        return ExecuteRestore(command, parameters);
                    case "list":
                        return ExecuteList(command);
                    case "play-start":
                        return ExecutePlayStart(command, parameters);
                    case "cross-refs":
                        return ExecuteCrossRefs(command);
                    case "list-loaded":
                        return ExecuteListLoaded(command);
                    case "preview-create":
                        return ExecutePreviewCreate(command);
                    case "preview-close":
                        return ExecutePreviewClose(command, parameters);
                    default:
                        return BridgeResponse.Error(
                            command.commandId,
                            command.commandType,
                            $"Unknown scene setup operation: {parameters.operation}. "
                            + "Supported: save, restore, list, play-start, cross-refs, "
                            + "list-loaded, preview-create, preview-close");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Scene setup operation error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse ExecuteSave(BridgeCommand command, SceneSetupParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.setupName))
            {
                return BridgeResponse.Error(
                    command.commandId, command.commandType, "Setup name is required");
            }

            if (!VALID_NAME_REGEX.IsMatch(parameters.setupName))
            {
                return BridgeResponse.Error(
                    command.commandId, command.commandType,
                    "Invalid setup name. Use alphanumeric, hyphens, and underscores only (max 64).");
            }

            Directory.CreateDirectory(SETUPS_PATH);

            var scenes = new List<SceneSetupEntry>();
            for (int i = 0; i < SceneManager.sceneCount; i++)
            {
                var scene = SceneManager.GetSceneAt(i);
                scenes.Add(new SceneSetupEntry
                {
                    path = scene.path,
                    isLoaded = scene.isLoaded,
                    isActive = scene == SceneManager.GetActiveScene(),
                    isSubScene = false
                });
            }

            var now = DateTime.UtcNow.ToString("o");
            var setupFile = new SceneSetupFile
            {
                name = parameters.setupName,
                createdAt = now,
                updatedAt = now,
                scenes = scenes
            };

            var filePath = Path.Combine(SETUPS_PATH, $"{parameters.setupName}.json");

            // Preserve createdAt if updating an existing setup
            if (File.Exists(filePath))
            {
                try
                {
                    var existing = JsonUtility.FromJson<SceneSetupFile>(
                        File.ReadAllText(filePath));
                    if (existing is not null && !string.IsNullOrEmpty(existing.createdAt))
                    {
                        setupFile.createdAt = existing.createdAt;
                    }
                }
                catch
                {
                    // Ignore parse errors on existing file
                }
            }

            File.WriteAllText(filePath, JsonUtility.ToJson(setupFile, true));

            var relativePath = $".claude/unity/scene-setups/{parameters.setupName}.json";
            var result = new SceneSetupResult
            {
                operation = "save",
                setupName = parameters.setupName,
                setupPath = relativePath,
                scenes = scenes,
                sceneCount = scenes.Count,
                success = true,
                message = $"Scene setup '{parameters.setupName}' saved with {scenes.Count} scenes"
            };

            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteRestore(BridgeCommand command, SceneSetupParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.setupName))
            {
                return BridgeResponse.Error(
                    command.commandId, command.commandType, "Setup name is required");
            }

            if (EditorApplication.isPlaying)
            {
                return BridgeResponse.Error(
                    command.commandId, command.commandType,
                    "Cannot restore scene setup while in Play mode");
            }

            var filePath = Path.Combine(SETUPS_PATH, $"{parameters.setupName}.json");
            if (!File.Exists(filePath))
            {
                return BridgeResponse.Error(
                    command.commandId, command.commandType,
                    $"Scene setup '{parameters.setupName}' not found");
            }

            var setupFile = JsonUtility.FromJson<SceneSetupFile>(File.ReadAllText(filePath));
            if (setupFile == null || setupFile.scenes == null || setupFile.scenes.Count == 0)
            {
                return BridgeResponse.Error(
                    command.commandId, command.commandType,
                    "Scene setup is empty or invalid (at least one scene required)");
            }

            // Pre-validate all scene paths exist on disk
            var missingScenes = new List<string>();
            foreach (var scene in setupFile.scenes)
            {
                var fullPath = Path.Combine(PROJECT_ROOT, scene.path);
                if (!File.Exists(fullPath))
                {
                    missingScenes.Add(scene.path);
                }
            }

            if (missingScenes.Count > 0)
            {
                var errorResult = new SceneSetupRestoreError
                {
                    operation = "restore",
                    setupName = parameters.setupName,
                    missingScenes = missingScenes,
                    success = false,
                    message = $"Cannot restore setup: {missingScenes.Count} scene(s) not found on disk"
                };
                return BridgeResponse.Success(
                    command.commandId, command.commandType, JsonUtility.ToJson(errorResult));
            }

            // Build SceneSetup array for RestoreSceneManagerSetup
            var sceneSetups = new SceneSetup[setupFile.scenes.Count];
            for (int i = 0; i < setupFile.scenes.Count; i++)
            {
                sceneSetups[i] = new SceneSetup
                {
                    path = setupFile.scenes[i].path,
                    isLoaded = setupFile.scenes[i].isLoaded,
                    isActive = setupFile.scenes[i].isActive
                };
            }

            EditorSceneManager.RestoreSceneManagerSetup(sceneSetups);

            var result = new SceneSetupResult
            {
                operation = "restore",
                setupName = parameters.setupName,
                scenes = setupFile.scenes,
                sceneCount = setupFile.scenes.Count,
                success = true,
                message = $"Scene setup '{parameters.setupName}' restored"
            };

            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteList(BridgeCommand command)
        {
            var result = new SceneSetupListResult
            {
                operation = "list",
                success = true
            };

            if (!Directory.Exists(SETUPS_PATH))
            {
                result.setupCount = 0;
                result.message = "No saved scene setups found";
                return BridgeResponse.Success(
                    command.commandId, command.commandType, JsonUtility.ToJson(result));
            }

            var files = Directory.GetFiles(SETUPS_PATH, "*.json");
            foreach (var file in files)
            {
                try
                {
                    var setupFile = JsonUtility.FromJson<SceneSetupFile>(File.ReadAllText(file));
                    if (setupFile is null) continue;

                    var activeScene = setupFile.scenes?.FirstOrDefault(s => s.isActive)?.path ?? "";
                    result.setups.Add(new SceneSetupSummary
                    {
                        name = setupFile.name,
                        sceneCount = setupFile.scenes?.Count ?? 0,
                        createdAt = setupFile.createdAt,
                        activeScene = activeScene
                    });
                }
                catch
                {
                    // Skip malformed files
                }
            }

            result.setupCount = result.setups.Count;
            result.message = $"Found {result.setupCount} saved scene setups";
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecutePlayStart(BridgeCommand command, SceneSetupParams parameters)
        {
            if (parameters.clear)
            {
                EditorSceneManager.playModeStartScene = null;
                var clearResult = new PlayStartResult
                {
                    operation = "play-start",
                    playModeStartScene = "",
                    isSet = false,
                    success = true,
                    message = "Play mode start scene cleared (will use active scene)"
                };
                return BridgeResponse.Success(
                    command.commandId, command.commandType, JsonUtility.ToJson(clearResult));
            }

            if (!string.IsNullOrEmpty(parameters.scenePath))
            {
                var sceneAsset = AssetDatabase.LoadAssetAtPath<SceneAsset>(parameters.scenePath);
                if (sceneAsset == null)
                {
                    return BridgeResponse.Error(
                        command.commandId, command.commandType,
                        $"Scene not found at path: {parameters.scenePath}");
                }

                EditorSceneManager.playModeStartScene = sceneAsset;
                var setResult = new PlayStartResult
                {
                    operation = "play-start",
                    playModeStartScene = parameters.scenePath,
                    isSet = true,
                    success = true,
                    message = $"Play mode start scene set to: {parameters.scenePath}"
                };
                return BridgeResponse.Success(
                    command.commandId, command.commandType, JsonUtility.ToJson(setResult));
            }

            // Get current play mode start scene
            var startScene = EditorSceneManager.playModeStartScene;
            var path = startScene != null ? AssetDatabase.GetAssetPath(startScene) : "";
            var getResult = new PlayStartResult
            {
                operation = "play-start",
                playModeStartScene = path,
                isSet = !string.IsNullOrEmpty(path),
                success = true,
                message = !string.IsNullOrEmpty(path)
                    ? $"Play mode start scene: {path}"
                    : "No play mode start scene set (will use active scene)"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(getResult));
        }

        private BridgeResponse ExecuteCrossRefs(BridgeCommand command)
        {
            var result = new CrossRefsResult
            {
                operation = "cross-refs",
                success = true
            };

            for (int i = 0; i < SceneManager.sceneCount; i++)
            {
                var scene = SceneManager.GetSceneAt(i);
                if (!scene.isLoaded) continue;

                result.loadedScenes.Add(scene.path);

                bool hasCrossRefs = EditorSceneManager.DetectCrossSceneReferences(scene);
                result.crossReferences.Add(new CrossRefInfo
                {
                    scenePath = scene.path,
                    hasCrossRefs = hasCrossRefs
                });

                if (hasCrossRefs) result.totalWithCrossRefs++;
            }

            result.message = $"Detected cross-scene references in {result.totalWithCrossRefs} "
                             + $"of {result.loadedScenes.Count} loaded scenes";
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteListLoaded(BridgeCommand command)
        {
            var result = new ListLoadedResult
            {
                operation = "list-loaded",
                success = true
            };

            var activeScene = SceneManager.GetActiveScene();
            for (int i = 0; i < SceneManager.sceneCount; i++)
            {
                var scene = SceneManager.GetSceneAt(i);
                if (!scene.isLoaded) continue;

                result.scenes.Add(new LoadedSceneInfo
                {
                    name = scene.name,
                    path = scene.path,
                    buildIndex = scene.buildIndex,
                    isLoaded = true,
                    isActive = scene == activeScene,
                    isDirty = scene.isDirty,
                    rootCount = scene.rootCount
                });
            }

            result.loadedCount = result.scenes.Count;
            result.message = $"{result.loadedCount} scenes currently loaded";
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecutePreviewCreate(BridgeCommand command)
        {
            var previewScene = EditorSceneManager.NewPreviewScene();
            int handle = _nextPreviewHandle++;
            _previewScenes[handle] = previewScene;

            var result = new PreviewCreateResult
            {
                operation = "preview-create",
                handle = handle,
                sceneName = $"preview_{handle}",
                success = true,
                message = $"Preview scene created (handle: {handle})"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecutePreviewClose(BridgeCommand command, SceneSetupParams parameters)
        {
            if (parameters.handle < 0)
            {
                return BridgeResponse.Error(
                    command.commandId, command.commandType, "Preview scene handle is required");
            }

            if (!_previewScenes.TryGetValue(parameters.handle, out var scene))
            {
                return BridgeResponse.Error(
                    command.commandId, command.commandType,
                    $"No preview scene found with handle: {parameters.handle}");
            }

            EditorSceneManager.ClosePreviewScene(scene);
            _previewScenes.Remove(parameters.handle);

            var result = new PreviewCloseResult
            {
                operation = "preview-close",
                handle = parameters.handle,
                success = true,
                message = $"Preview scene closed (handle: {parameters.handle})"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }
    }
}

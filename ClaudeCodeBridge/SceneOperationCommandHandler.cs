using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for scene operations in Unity Editor.
    ///
    /// PURPOSE:
    /// Provides programmatic control over Unity scene management including loading,
    /// saving, creating, and listing scenes. Enables automated scene manipulation
    /// from external tools like Claude Code.
    ///
    /// USE CASES:
    /// - Load specific scenes for testing or inspection
    /// - Save current scene changes before switching contexts
    /// - Create new empty scenes programmatically
    /// - List all scenes in build settings for validation
    /// - Automate scene workflows in CI/CD pipelines
    ///
    /// COMMAND JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "scene-operation",
    ///   "timestamp": "2025-10-06T12:00:00Z",
    ///   "parametersJson": "{\"operation\":\"load\",\"scenePath\":\"Assets/Scenes/GameplayScene.unity\",\"saveCurrentScene\":true}"
    /// }
    ///
    /// USAGE EXAMPLES:
    ///
    /// 1. Load a specific scene:
    ///    send-command.ps1 -CommandType "scene-operation" -Parameters @{operation="load"; scenePath="Assets/Scenes/GameplayScene.unity"}
    ///
    /// 2. Save current scene:
    ///    send-command.ps1 -CommandType "scene-operation" -Parameters @{operation="save"}
    ///
    /// 3. Create new empty scene:
    ///    send-command.ps1 -CommandType "scene-operation" -Parameters @{operation="create"; scenePath="Assets/Scenes/NewScene.unity"}
    ///
    /// 4. List all scenes in build settings:
    ///    send-command.ps1 -CommandType "scene-operation" -Parameters @{operation="list"}
    /// </summary>
    public class SceneOperationCommandHandler : ICommandHandler
    {
        public string CommandType => "scene-operation";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<SceneOperationParams>(command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new SceneOperationParams();

                BridgeLogger.LogDebug($"Executing operation: {parameters.operation}");

                SceneOperationResult result = null;

                switch (parameters.operation?.ToLower())
                {
                    case "load":
                        result = LoadScene(parameters);
                        break;

                    case "save":
                        result = SaveScene(parameters);
                        break;

                    case "create":
                        result = CreateScene(parameters);
                        break;

                    case "list":
                        result = ListScenes(parameters);
                        break;

                    default:
                        return BridgeResponse.Error(
                            command.commandId,
                            command.commandType,
                            $"Unknown operation: {parameters.operation}. Supported operations: load, save, create, list"
                        );
                }

                if (result.success)
                {
                    var resultJson = JsonUtility.ToJson(result);
                    return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
                }
                else
                {
                    return BridgeResponse.Error(command.commandId, command.commandType, result.message);
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        /// <summary>
        /// Load a scene by path.
        /// Validates the scene exists and optionally saves the current scene before loading.
        /// </summary>
        private SceneOperationResult LoadScene(SceneOperationParams parameters)
        {
            var result = new SceneOperationResult
            {
                operation = "load"
            };

            // Validate scene path
            if (string.IsNullOrEmpty(parameters.scenePath))
            {
                result.success = false;
                result.message = "Scene path is required for load operation";
                return result;
            }

            // Check if scene exists in AssetDatabase
            var sceneAsset = AssetDatabase.LoadAssetAtPath<SceneAsset>(parameters.scenePath);
            if (sceneAsset == null)
            {
                result.success = false;
                result.message = $"Scene not found at path: {parameters.scenePath}";
                return result;
            }

            // Save current scene if requested
            if (parameters.saveCurrentScene)
            {
                var currentScene = SceneManager.GetActiveScene();
                if (currentScene.isDirty)
                {
                    bool saved = EditorSceneManager.SaveScene(currentScene);
                    if (!saved)
                    {
                        result.success = false;
                        result.message = "Failed to save current scene before loading";
                        return result;
                    }
                    BridgeLogger.LogDebug($"Saved current scene: {currentScene.path}");
                }
            }

            // Load the scene
            try
            {
                var scene = EditorSceneManager.OpenScene(parameters.scenePath, OpenSceneMode.Single);
                result.success = true;
                result.currentScenePath = scene.path;
                result.message = $"Successfully loaded scene: {scene.name}";
                BridgeLogger.LogInfo($"Loaded scene: {scene.path}");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to load scene: {ex.Message}";
            }

            return result;
        }

        /// <summary>
        /// Save the current active scene.
        /// </summary>
        private SceneOperationResult SaveScene(SceneOperationParams parameters)
        {
            var result = new SceneOperationResult
            {
                operation = "save"
            };

            var currentScene = SceneManager.GetActiveScene();
            result.currentScenePath = currentScene.path;

            // Check if scene has unsaved changes
            if (!currentScene.isDirty)
            {
                result.success = true;
                result.message = $"Scene has no unsaved changes: {currentScene.name}";
                return result;
            }

            // Save the scene
            try
            {
                bool saved = EditorSceneManager.SaveScene(currentScene);
                if (saved)
                {
                    result.success = true;
                    result.message = $"Successfully saved scene: {currentScene.name}";
                    BridgeLogger.LogInfo($"Saved scene: {currentScene.path}");
                }
                else
                {
                    result.success = false;
                    result.message = "Failed to save scene (user may have cancelled)";
                }
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to save scene: {ex.Message}";
            }

            return result;
        }

        /// <summary>
        /// Create a new empty scene.
        /// </summary>
        private SceneOperationResult CreateScene(SceneOperationParams parameters)
        {
            var result = new SceneOperationResult
            {
                operation = "create"
            };

            // Validate scene path
            if (string.IsNullOrEmpty(parameters.scenePath))
            {
                result.success = false;
                result.message = "Scene path is required for create operation";
                return result;
            }

            // Validate path ends with .unity
            if (!parameters.scenePath.EndsWith(".unity"))
            {
                result.success = false;
                result.message = "Scene path must end with .unity extension";
                return result;
            }

            // Validate path starts with Assets/
            if (!parameters.scenePath.StartsWith("Assets/"))
            {
                result.success = false;
                result.message = "Scene path must start with 'Assets/'";
                return result;
            }

            // Save current scene if requested
            if (parameters.saveCurrentScene)
            {
                var currentScene = SceneManager.GetActiveScene();
                if (currentScene.isDirty)
                {
                    bool saved = EditorSceneManager.SaveScene(currentScene);
                    if (!saved)
                    {
                        result.success = false;
                        result.message = "Failed to save current scene before creating new one";
                        return result;
                    }
                }
            }

            // Create new scene
            try
            {
                var newScene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);

                // Save the new scene to the specified path
                bool saved = EditorSceneManager.SaveScene(newScene, parameters.scenePath);
                if (saved)
                {
                    result.success = true;
                    result.currentScenePath = newScene.path;
                    result.message = $"Successfully created scene: {parameters.scenePath}";
                    BridgeLogger.LogInfo($"Created scene: {newScene.path}");
                }
                else
                {
                    result.success = false;
                    result.message = "Failed to save new scene (user may have cancelled)";
                }
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to create scene: {ex.Message}";
            }

            return result;
        }

        /// <summary>
        /// List all scenes in the build settings.
        /// </summary>
        private SceneOperationResult ListScenes(SceneOperationParams parameters)
        {
            var result = new SceneOperationResult
            {
                operation = "list"
            };

            try
            {
                var currentScene = SceneManager.GetActiveScene();
                result.currentScenePath = currentScene.path;

                // Get all scenes from build settings
                var buildScenes = EditorBuildSettings.scenes;
                foreach (var buildScene in buildScenes)
                {
                    if (buildScene.enabled)
                    {
                        result.scenePaths.Add(buildScene.path);
                    }
                }

                // Also find all scene assets in the project
                var sceneGuids = AssetDatabase.FindAssets("t:Scene");
                var allScenePaths = sceneGuids
                    .Select(guid => AssetDatabase.GUIDToAssetPath(guid))
                    .Where(path => !string.IsNullOrEmpty(path))
                    .OrderBy(path => path)
                    .ToList();

                // Add scenes not in build settings (for completeness)
                foreach (var scenePath in allScenePaths)
                {
                    if (!result.scenePaths.Contains(scenePath))
                    {
                        result.scenePaths.Add(scenePath);
                    }
                }

                result.success = true;
                result.message = $"Found {result.scenePaths.Count} scenes in project";
                BridgeLogger.LogInfo($"Listed {result.scenePaths.Count} scenes");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to list scenes: {ex.Message}";
            }

            return result;
        }
    }
}

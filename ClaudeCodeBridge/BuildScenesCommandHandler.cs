using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for managing Build Settings scene list.
    ///
    /// PURPOSE:
    /// Provides programmatic control over EditorBuildSettings.scenes,
    /// enabling automated build pipeline configuration from external tools.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "list" - List all scenes in Build Settings
    /// 2. "add" - Add a scene to the Build Settings list
    /// 3. "remove" - Remove a scene from the Build Settings list
    /// 4. "enable" - Enable a scene in the Build Settings list
    /// 5. "disable" - Disable a scene in the Build Settings list
    /// 6. "reorder" - Move a scene to a new index position
    /// </summary>
    public class BuildScenesCommandHandler : ICommandHandler
    {
        public string CommandType => "build-scenes";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<BuildScenesParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new BuildScenesParams();

                var operation = parameters.operation?.ToLower();
                BridgeLogger.LogDebug($"Executing build-scenes: {operation}");

                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Cannot execute while scripts are compiling.");
                }

                // Guard: mutating operations not allowed during play mode
                if (EditorApplication.isPlaying && operation != "list")
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Mutating build scene operations are not supported during play mode.");
                }

                switch (operation)
                {
                    case "list":
                        return HandleList(command);
                    case "add":
                        return HandleAdd(command, parameters);
                    case "remove":
                        return HandleRemove(command, parameters);
                    case "enable":
                        return HandleEnable(command, parameters, true);
                    case "disable":
                        return HandleEnable(command, parameters, false);
                    case "reorder":
                        return HandleReorder(command, parameters);
                    default:
                        return BridgeResponse.Error(command.commandId, command.commandType,
                            $"Unknown operation: {parameters.operation}. " +
                            "Supported: list, add, remove, enable, disable, reorder");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Build-scenes error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse HandleList(BridgeCommand command)
        {
            var scenes = EditorBuildSettings.scenes;
            var result = new BuildScenesResult
            {
                success = true,
                operation = "list",
                count = scenes.Length,
            };

            for (int i = 0; i < scenes.Length; i++)
            {
                result.scenes.Add(new BuildSceneInfo
                {
                    path = scenes[i].path,
                    enabled = scenes[i].enabled,
                    guid = scenes[i].guid.ToString(),
                    index = i,
                });
            }

            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse HandleAdd(BridgeCommand command, BuildScenesParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.scenePath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "scenePath is required for add operation.");
            }

            // Verify scene asset exists
            var sceneGuid = AssetDatabase.AssetPathToGUID(parameters.scenePath);
            if (string.IsNullOrEmpty(sceneGuid))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Scene asset not found: {parameters.scenePath}");
            }

            var scenesList = new List<EditorBuildSettingsScene>(EditorBuildSettings.scenes);

            // Check if already present
            if (scenesList.Any(s => s.path == parameters.scenePath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Scene already in Build Settings: {parameters.scenePath}");
            }

            var newScene = new EditorBuildSettingsScene(parameters.scenePath, true);

            if (parameters.index >= 0 && parameters.index < scenesList.Count)
                scenesList.Insert(parameters.index, newScene);
            else
                scenesList.Add(newScene);

            EditorBuildSettings.scenes = scenesList.ToArray();

            var result = new BuildScenesResult
            {
                success = true,
                operation = "add",
                scenePath = parameters.scenePath,
                count = scenesList.Count,
            };
            BridgeLogger.LogInfo($"Build scene added: {parameters.scenePath}");
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse HandleRemove(BridgeCommand command, BuildScenesParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.scenePath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "scenePath is required for remove operation.");
            }

            var scenesList = new List<EditorBuildSettingsScene>(EditorBuildSettings.scenes);
            int removed = scenesList.RemoveAll(s => s.path == parameters.scenePath);

            if (removed == 0)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Scene not found in Build Settings: {parameters.scenePath}");
            }

            EditorBuildSettings.scenes = scenesList.ToArray();

            var result = new BuildScenesResult
            {
                success = true,
                operation = "remove",
                scenePath = parameters.scenePath,
                count = scenesList.Count,
            };
            BridgeLogger.LogInfo($"Build scene removed: {parameters.scenePath}");
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse HandleEnable(
            BridgeCommand command, BuildScenesParams parameters, bool enable)
        {
            if (string.IsNullOrEmpty(parameters.scenePath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"scenePath is required for {(enable ? "enable" : "disable")} operation.");
            }

            var scenes = EditorBuildSettings.scenes;
            bool found = false;

            for (int i = 0; i < scenes.Length; i++)
            {
                if (scenes[i].path == parameters.scenePath)
                {
                    scenes[i].enabled = enable;
                    found = true;
                    break;
                }
            }

            if (!found)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Scene not found in Build Settings: {parameters.scenePath}");
            }

            EditorBuildSettings.scenes = scenes;

            var result = new BuildScenesResult
            {
                success = true,
                operation = enable ? "enable" : "disable",
                scenePath = parameters.scenePath,
                enabled = enable,
                count = scenes.Length,
            };
            BridgeLogger.LogInfo($"Build scene {(enable ? "enabled" : "disabled")}: " +
                parameters.scenePath);
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse HandleReorder(BridgeCommand command, BuildScenesParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.scenePath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "scenePath is required for reorder operation.");
            }

            if (parameters.index < 0)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "index must be >= 0 for reorder operation.");
            }

            var scenesList = new List<EditorBuildSettingsScene>(EditorBuildSettings.scenes);
            int currentIndex = scenesList.FindIndex(s => s.path == parameters.scenePath);

            if (currentIndex < 0)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Scene not found in Build Settings: {parameters.scenePath}");
            }

            var scene = scenesList[currentIndex];
            scenesList.RemoveAt(currentIndex);

            int newIndex = Math.Min(parameters.index, scenesList.Count);
            scenesList.Insert(newIndex, scene);

            EditorBuildSettings.scenes = scenesList.ToArray();

            var result = new BuildScenesResult
            {
                success = true,
                operation = "reorder",
                scenePath = parameters.scenePath,
                newIndex = newIndex,
                count = scenesList.Count,
            };
            BridgeLogger.LogInfo($"Build scene reordered: {parameters.scenePath} -> index {newIndex}");
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }
    }

    #region Build Scenes Models

    [Serializable]
    public class BuildScenesParams
    {
        public string operation;
        public string scenePath;
        public int index = -1;
    }

    [Serializable]
    public class BuildScenesResult
    {
        public bool success;
        public string operation;
        public string scenePath;
        public bool enabled;
        public int count;
        public int newIndex;
        public List<BuildSceneInfo> scenes = new List<BuildSceneInfo>();
    }

    [Serializable]
    public class BuildSceneInfo
    {
        public string path;
        public bool enabled;
        public string guid;
        public int index;
    }

    #endregion
}

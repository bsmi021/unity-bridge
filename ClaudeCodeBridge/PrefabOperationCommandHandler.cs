using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for prefab operations.
    /// Supports: create, instantiate, apply, revert, get-info.
    /// Helper methods in PrefabOperationHelpers.cs (partial class).
    /// </summary>
    public partial class PrefabOperationCommandHandler : ICommandHandler
    {
        public string CommandType => "prefab-operation";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<PrefabOperationParams>(command.parametersJson ?? "{}");
                if (parameters == null || string.IsNullOrEmpty(parameters.operation))
                {
                    return BridgeResponse.Error(command.commandId, command.commandType, "Missing required parameter: operation");
                }

                BridgeLogger.LogDebug($"Executing operation: {parameters.operation}");

                // Route to appropriate operation handler
                PrefabOperationResult result;
                switch (parameters.operation.ToLower())
                {
                    case "create":
                        result = CreatePrefab(parameters);
                        break;
                    case "instantiate":
                        result = InstantiatePrefab(parameters);
                        break;
                    case "destroy":
                        result = DestroyPrefabInstance(parameters);
                        break;
                    case "apply":
                        result = ApplyPrefabModifications(parameters);
                        break;
                    case "revert":
                        result = RevertPrefabModifications(parameters);
                        break;
                    case "get-info":
                        result = GetPrefabInfo(parameters);
                        break;
                    default:
                        return BridgeResponse.Error(command.commandId, command.commandType,
                            $"Unknown operation: {parameters.operation}. Supported: "
                            + "create, instantiate, destroy, apply, revert, get-info");
                }

                var resultJson = JsonUtility.ToJson(result);
                BridgeLogger.LogInfo($"Operation completed: {parameters.operation}");

                return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        #region Operation Handlers

        /// <summary>
        /// Create a new prefab from a GameObject in the scene.
        /// Uses PrefabUtility.SaveAsPrefabAsset to create the prefab.
        /// </summary>
        private PrefabOperationResult CreatePrefab(PrefabOperationParams parameters)
        {
            var result = new PrefabOperationResult { operation = "create" };

            // Validate parameters
            if (string.IsNullOrEmpty(parameters.gameObjectPath))
            {
                result.success = false;
                result.message = "Missing required parameter: gameObjectPath";
                return result;
            }

            if (string.IsNullOrEmpty(parameters.prefabPath))
            {
                result.success = false;
                result.message = "Missing required parameter: prefabPath";
                return result;
            }

            // Find source GameObject
            var sourceObject = FindGameObject(parameters.gameObjectPath);
            if (sourceObject == null)
            {
                result.success = false;
                result.message = $"GameObject not found: {parameters.gameObjectPath}";
                return result;
            }

            // Validate prefab path
            if (!parameters.prefabPath.StartsWith("Assets/") || !parameters.prefabPath.EndsWith(".prefab"))
            {
                result.success = false;
                result.message = $"Invalid prefab path: {parameters.prefabPath}. Must start with 'Assets/' and end with '.prefab'";
                return result;
            }

            // Ensure directory exists
            var directory = System.IO.Path.GetDirectoryName(parameters.prefabPath);
            if (!AssetDatabase.IsValidFolder(directory))
            {
                // Create folders if they don't exist
                var folders = directory.Split('/');
                var currentPath = folders[0];
                for (int i = 1; i < folders.Length; i++)
                {
                    var newFolder = currentPath + "/" + folders[i];
                    if (!AssetDatabase.IsValidFolder(newFolder))
                    {
                        AssetDatabase.CreateFolder(currentPath, folders[i]);
                    }
                    currentPath = newFolder;
                }
            }

            // Create prefab
            var prefab = PrefabUtility.SaveAsPrefabAsset(sourceObject, parameters.prefabPath);
            if (prefab == null)
            {
                result.success = false;
                result.message = $"Failed to create prefab at: {parameters.prefabPath}";
                return result;
            }

            result.success = true;
            result.prefabPath = parameters.prefabPath;
            result.gameObjectPath = parameters.gameObjectPath;
            result.message = $"Successfully created prefab: {parameters.prefabPath}";

            return result;
        }

        /// <summary>
        /// Instantiate a prefab into the scene.
        /// Uses PrefabUtility.InstantiatePrefab to maintain prefab connection.
        /// </summary>
        private PrefabOperationResult InstantiatePrefab(PrefabOperationParams parameters)
        {
            var result = new PrefabOperationResult { operation = "instantiate" };

            // Validate parameters
            if (string.IsNullOrEmpty(parameters.prefabPath))
            {
                result.success = false;
                result.message = "Missing required parameter: prefabPath";
                return result;
            }

            // Load prefab asset
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(parameters.prefabPath);
            if (prefab == null)
            {
                result.success = false;
                result.message = $"Prefab not found: {parameters.prefabPath}";
                return result;
            }

            // Find parent GameObject if specified
            Transform parent = null;
            if (!string.IsNullOrEmpty(parameters.gameObjectPath))
            {
                var parentObject = FindGameObject(parameters.gameObjectPath);
                if (parentObject == null)
                {
                    result.success = false;
                    result.message = $"Parent GameObject not found: {parameters.gameObjectPath}";
                    return result;
                }
                parent = parentObject.transform;
            }

            // Instantiate prefab
            var instance = PrefabUtility.InstantiatePrefab(prefab, parent) as GameObject;
            if (instance == null)
            {
                result.success = false;
                result.message = $"Failed to instantiate prefab: {parameters.prefabPath}";
                return result;
            }

            if (parameters.position != null && parameters.position.isSet)
            {
                instance.transform.position = new Vector3(
                    parameters.position.x,
                    parameters.position.y,
                    parameters.position.z);
            }

            // Get full path of instantiated object
            result.success = true;
            result.prefabPath = parameters.prefabPath;
            result.gameObjectPath = GetGameObjectPath(instance);
            result.isPrefabInstance = true;
            result.message = $"Successfully instantiated prefab at: {result.gameObjectPath}";

            return result;
        }

        /// <summary>
        /// Apply modifications from a prefab instance back to the prefab asset.
        /// Uses PrefabUtility.ApplyPrefabInstance to apply changes.
        /// </summary>
        private PrefabOperationResult ApplyPrefabModifications(PrefabOperationParams parameters)
        {
            var result = new PrefabOperationResult { operation = "apply" };

            // Validate parameters
            if (string.IsNullOrEmpty(parameters.gameObjectPath))
            {
                result.success = false;
                result.message = "Missing required parameter: gameObjectPath";
                return result;
            }

            // Find GameObject
            var gameObject = FindGameObject(parameters.gameObjectPath);
            if (gameObject == null)
            {
                result.success = false;
                result.message = $"GameObject not found: {parameters.gameObjectPath}";
                return result;
            }

            // Check if it's a prefab instance
            if (!PrefabUtility.IsPartOfPrefabInstance(gameObject))
            {
                result.success = false;
                result.message = $"GameObject is not a prefab instance: {parameters.gameObjectPath}";
                return result;
            }

            // Get prefab instance root
            var prefabRoot = PrefabUtility.GetOutermostPrefabInstanceRoot(gameObject);
            if (prefabRoot == null)
            {
                result.success = false;
                result.message = $"Failed to get prefab instance root for: {parameters.gameObjectPath}";
                return result;
            }

            // Get prefab asset path
            var prefabAsset = PrefabUtility.GetCorrespondingObjectFromSource(prefabRoot);
            var assetPath = AssetDatabase.GetAssetPath(prefabAsset);

            // Get modifications before applying
            var modifications = GetPrefabModifications(prefabRoot);

            // Apply modifications
            var action = parameters.applyToAll
                ? InteractionMode.AutomatedAction
                : InteractionMode.UserAction;

            PrefabUtility.ApplyPrefabInstance(prefabRoot, action);

            result.success = true;
            result.prefabPath = assetPath;
            result.gameObjectPath = parameters.gameObjectPath;
            result.isPrefabInstance = true;
            result.hasModifications = false; // No modifications after applying
            result.modifications = modifications;
            result.message = $"Successfully applied modifications to prefab: {assetPath}";

            return result;
        }

        /// <summary>
        /// Revert modifications on a prefab instance back to prefab defaults.
        /// Uses PrefabUtility.RevertPrefabInstance to revert changes.
        /// </summary>
        private PrefabOperationResult RevertPrefabModifications(PrefabOperationParams parameters)
        {
            var result = new PrefabOperationResult { operation = "revert" };

            // Validate parameters
            if (string.IsNullOrEmpty(parameters.gameObjectPath))
            {
                result.success = false;
                result.message = "Missing required parameter: gameObjectPath";
                return result;
            }

            // Find GameObject
            var gameObject = FindGameObject(parameters.gameObjectPath);
            if (gameObject == null)
            {
                result.success = false;
                result.message = $"GameObject not found: {parameters.gameObjectPath}";
                return result;
            }

            // Check if it's a prefab instance
            if (!PrefabUtility.IsPartOfPrefabInstance(gameObject))
            {
                result.success = false;
                result.message = $"GameObject is not a prefab instance: {parameters.gameObjectPath}";
                return result;
            }

            // Get prefab instance root
            var prefabRoot = PrefabUtility.GetOutermostPrefabInstanceRoot(gameObject);
            if (prefabRoot == null)
            {
                result.success = false;
                result.message = $"Failed to get prefab instance root for: {parameters.gameObjectPath}";
                return result;
            }

            // Get prefab asset path
            var prefabAsset = PrefabUtility.GetCorrespondingObjectFromSource(prefabRoot);
            var assetPath = AssetDatabase.GetAssetPath(prefabAsset);

            // Get modifications before reverting
            var modifications = GetPrefabModifications(prefabRoot);

            // Revert modifications
            PrefabUtility.RevertPrefabInstance(prefabRoot, InteractionMode.AutomatedAction);

            result.success = true;
            result.prefabPath = assetPath;
            result.gameObjectPath = parameters.gameObjectPath;
            result.isPrefabInstance = true;
            result.hasModifications = false; // No modifications after reverting
            result.modifications = modifications;
            result.message = $"Successfully reverted modifications on prefab instance: {parameters.gameObjectPath}";

            return result;
        }

        /// <summary>
        /// Get information about a prefab instance including its status and modifications.
        /// </summary>
        private PrefabOperationResult GetPrefabInfo(PrefabOperationParams parameters)
        {
            var result = new PrefabOperationResult { operation = "get-info" };

            // Validate parameters
            if (string.IsNullOrEmpty(parameters.gameObjectPath))
            {
                result.success = false;
                result.message = "Missing required parameter: gameObjectPath";
                return result;
            }

            // Find GameObject
            var gameObject = FindGameObject(parameters.gameObjectPath);
            if (gameObject == null)
            {
                result.success = false;
                result.message = $"GameObject not found: {parameters.gameObjectPath}";
                return result;
            }

            result.gameObjectPath = parameters.gameObjectPath;

            // Check if it's a prefab instance
            result.isPrefabInstance = PrefabUtility.IsPartOfPrefabInstance(gameObject);

            if (!result.isPrefabInstance)
            {
                result.success = true;
                result.message = $"GameObject is not a prefab instance: {parameters.gameObjectPath}";
                return result;
            }

            // Get prefab asset path
            var prefabAsset = PrefabUtility.GetCorrespondingObjectFromSource(gameObject);
            if (prefabAsset != null)
            {
                result.prefabPath = AssetDatabase.GetAssetPath(prefabAsset);
            }

            // Get prefab instance root for modification checks
            var prefabRoot = PrefabUtility.GetOutermostPrefabInstanceRoot(gameObject);
            if (prefabRoot != null)
            {
                // Check for modifications
                result.hasModifications = PrefabUtility.HasPrefabInstanceAnyOverrides(prefabRoot, false);

                if (result.hasModifications)
                {
                    result.modifications = GetPrefabModifications(prefabRoot);
                }
            }

            result.success = true;
            result.message = result.hasModifications
                ? $"Prefab instance has {result.modifications.Count} modification(s)"
                : "Prefab instance has no modifications";

            return result;
        }

        #endregion

        // Helper methods (FindGameObject, GetGameObjectPath, GetPrefabModifications)
        // are in PrefabOperationHelpers.cs (partial class).
    }
}

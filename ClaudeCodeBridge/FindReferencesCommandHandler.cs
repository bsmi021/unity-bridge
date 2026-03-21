using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for finding asset references in loaded scenes.
    ///
    /// PURPOSE:
    /// Given an asset path, iterates all components in loaded scenes using
    /// SerializedObject/SerializedProperty to find ObjectReference properties
    /// that reference the target asset.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "find-in-scene" - Find all references to an asset in loaded scenes
    ///
    /// COMMAND JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "find-references",
    ///   "parametersJson": "{\"operation\":\"find-in-scene\",\"assetPath\":\"Assets/Materials/Red.mat\"}"
    /// }
    /// </summary>
    public class FindReferencesCommandHandler : ICommandHandler
    {
        public string CommandType => "find-references";

        private const int MAX_RESULTS = 500;

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<FindReferencesParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new FindReferencesParams();

                var operation = parameters.operation?.ToLower();
                BridgeLogger.LogDebug($"Find references operation: {operation}");

                switch (operation)
                {
                    case "find-in-scene":
                        return HandleFindInScene(command, parameters);
                    default:
                        return BridgeResponse.Error(command.commandId, command.commandType,
                            $"Unknown operation: {parameters.operation}. Supported: find-in-scene");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Find references error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse HandleFindInScene(
            BridgeCommand command, FindReferencesParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.assetPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "assetPath is required for find-in-scene operation.");
            }

            var targetAsset = AssetDatabase.LoadMainAssetAtPath(parameters.assetPath);
            if (targetAsset == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Asset not found at path: {parameters.assetPath}");
            }

            var result = new FindReferencesResult
            {
                operation = "find-in-scene",
                assetPath = parameters.assetPath,
                assetType = targetAsset.GetType().Name,
                success = true,
            };

            // Iterate all loaded scenes
            int sceneCount = SceneManager.sceneCount;
            for (int s = 0; s < sceneCount; s++)
            {
                var scene = SceneManager.GetSceneAt(s);
                if (!scene.isLoaded) continue;

                SearchScene(scene, targetAsset, result);

                if (result.references.Count >= MAX_RESULTS)
                {
                    result.truncated = true;
                    break;
                }
            }

            result.totalReferences = result.references.Count;
            result.message = $"Found {result.totalReferences} references to " +
                $"{parameters.assetPath} in loaded scenes" +
                (result.truncated ? $" (truncated at {MAX_RESULTS})" : "");

            BridgeLogger.LogInfo(result.message);
            return BridgeResponse.Success(
                command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private void SearchScene(
            Scene scene, UnityEngine.Object targetAsset, FindReferencesResult result)
        {
            foreach (var rootGo in scene.GetRootGameObjects())
            {
                SearchGameObjectRecursive(rootGo, targetAsset, result);
                if (result.references.Count >= MAX_RESULTS)
                    return;
            }
        }

        private void SearchGameObjectRecursive(
            GameObject go, UnityEngine.Object targetAsset, FindReferencesResult result)
        {
            var components = go.GetComponents<Component>();
            foreach (var component in components)
            {
                if (component == null) continue;
                SearchComponent(go, component, targetAsset, result);
                if (result.references.Count >= MAX_RESULTS)
                    return;
            }

            // Recurse children
            for (int i = 0; i < go.transform.childCount; i++)
            {
                SearchGameObjectRecursive(
                    go.transform.GetChild(i).gameObject, targetAsset, result);
                if (result.references.Count >= MAX_RESULTS)
                    return;
            }
        }

        private void SearchComponent(
            GameObject go,
            Component component,
            UnityEngine.Object targetAsset,
            FindReferencesResult result)
        {
            try
            {
                var so = new SerializedObject(component);
                var prop = so.GetIterator();

                while (prop.NextVisible(true))
                {
                    if (prop.propertyType != SerializedPropertyType.ObjectReference)
                        continue;

                    if (prop.objectReferenceValue == targetAsset)
                    {
                        result.references.Add(new AssetReference
                        {
                            gameObjectPath = GetGameObjectPath(go),
                            sceneName = go.scene.name,
                            componentType = component.GetType().Name,
                            propertyPath = prop.propertyPath,
                        });

                        if (result.references.Count >= MAX_RESULTS)
                            return;
                    }
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogDebug(
                    $"Skipped component {component.GetType().Name} on {go.name}: {ex.Message}");
            }
        }

        private string GetGameObjectPath(GameObject go)
        {
            if (go.transform.parent == null)
                return go.name;
            return $"{GetGameObjectPath(go.transform.parent.gameObject)}/{go.name}";
        }
    }

    #region Find References Models

    [Serializable]
    public class FindReferencesParams
    {
        public string operation; // "find-in-scene"
        public string assetPath; // Asset to search for
    }

    [Serializable]
    public class FindReferencesResult
    {
        public string operation;
        public string assetPath;
        public string assetType;
        public int totalReferences;
        public bool truncated;
        public List<AssetReference> references = new List<AssetReference>();
        public bool success;
        public string message;
    }

    [Serializable]
    public class AssetReference
    {
        public string gameObjectPath;
        public string sceneName;
        public string componentType;
        public string propertyPath;
    }

    #endregion
}

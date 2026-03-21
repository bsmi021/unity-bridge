using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for MonoScript inspection.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "info" - Get class info from a script asset path
    /// 2. "list" - List all MonoScripts in project with class names
    /// 3. "find-component" - Find the script for a component on a GameObject
    /// </summary>
    public class MonoScriptCommandHandler : ICommandHandler
    {
        public string CommandType => "script-info";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<MonoScriptParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new MonoScriptParams();

                var operation = parameters.operation?.ToLower() ?? "info";
                BridgeLogger.LogDebug($"Executing script-info: {operation}");

                switch (operation)
                {
                    case "info":
                        return HandleInfo(command, parameters);
                    case "list":
                        return HandleList(command, parameters);
                    case "find-component":
                        return HandleFindComponent(command, parameters);
                    default:
                        return BridgeResponse.Error(command.commandId, command.commandType,
                            $"Unknown operation: {parameters.operation}. " +
                            "Supported: info, list, find-component");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Script-info error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse HandleInfo(BridgeCommand command, MonoScriptParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.assetPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "assetPath is required for info operation.");
            }

            var script = AssetDatabase.LoadAssetAtPath<MonoScript>(parameters.assetPath);
            if (script == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"MonoScript not found at: {parameters.assetPath}");
            }

            var scriptClass = script.GetClass();
            var info = BuildScriptInfo(script, parameters.assetPath, scriptClass);

            var result = new MonoScriptResult
            {
                success = true,
                operation = "info",
                script = info,
                message = $"Script info for {parameters.assetPath}",
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse HandleList(BridgeCommand command, MonoScriptParams parameters)
        {
            var guids = AssetDatabase.FindAssets("t:MonoScript");
            var scripts = new List<MonoScriptInfo>();
            int maxResults = parameters.maxResults > 0 ? parameters.maxResults : 500;
            string filter = parameters.filter;

            foreach (var guid in guids)
            {
                if (scripts.Count >= maxResults) break;

                var path = AssetDatabase.GUIDToAssetPath(guid);

                // Only include user scripts (Assets/ folder)
                if (!path.StartsWith("Assets/")) continue;

                var script = AssetDatabase.LoadAssetAtPath<MonoScript>(path);
                if (script == null) continue;

                var scriptClass = script.GetClass();
                string className = scriptClass?.Name ?? script.name;

                if (!string.IsNullOrEmpty(filter) &&
                    !className.Contains(filter, StringComparison.OrdinalIgnoreCase) &&
                    !path.Contains(filter, StringComparison.OrdinalIgnoreCase))
                    continue;

                scripts.Add(BuildScriptInfo(script, path, scriptClass));
            }

            var result = new MonoScriptResult
            {
                success = true,
                operation = "list",
                scripts = scripts,
                totalCount = scripts.Count,
                message = $"Found {scripts.Count} scripts",
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse HandleFindComponent(
            BridgeCommand command, MonoScriptParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.gameObjectPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "gameObjectPath is required for find-component operation.");
            }
            if (string.IsNullOrEmpty(parameters.componentType))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "componentType is required for find-component operation.");
            }

            var go = FindGameObjectByPath(parameters.gameObjectPath);
            if (go == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"GameObject not found: {parameters.gameObjectPath}");
            }

            var component = go.GetComponents<MonoBehaviour>()
                .FirstOrDefault(c =>
                    c is not null &&
                    (c.GetType().Name == parameters.componentType ||
                     c.GetType().FullName == parameters.componentType));

            if (component == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"MonoBehaviour '{parameters.componentType}' not found on " +
                    $"{parameters.gameObjectPath}");
            }

            var script = MonoScript.FromMonoBehaviour(component);
            if (script == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"MonoScript not found for {parameters.componentType}");
            }

            var scriptPath = AssetDatabase.GetAssetPath(script);
            var info = BuildScriptInfo(script, scriptPath, component.GetType());

            var result = new MonoScriptResult
            {
                success = true,
                operation = "find-component",
                script = info,
                message = $"Found script for {parameters.componentType}",
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private static MonoScriptInfo BuildScriptInfo(
            MonoScript script, string path, Type scriptClass)
        {
            return new MonoScriptInfo
            {
                path = path,
                className = scriptClass?.Name ?? script.name,
                namespaceName = scriptClass?.Namespace ?? "",
                fullName = scriptClass?.FullName ?? script.name,
                assemblyName = scriptClass?.Assembly?.GetName()?.Name ?? "",
                isMonoBehaviour = scriptClass is not null &&
                    typeof(MonoBehaviour).IsAssignableFrom(scriptClass),
                isScriptableObject = scriptClass is not null &&
                    typeof(ScriptableObject).IsAssignableFrom(scriptClass),
                isEditor = scriptClass is not null &&
                    typeof(UnityEditor.Editor).IsAssignableFrom(scriptClass),
            };
        }

        private static GameObject FindGameObjectByPath(string path)
        {
            var parts = path.Split('/');
            var rootObjects = UnityEngine.SceneManagement.SceneManager
                .GetActiveScene().GetRootGameObjects();
            var current = rootObjects.FirstOrDefault(go => go.name == parts[0]);
            if (current == null) return null;

            for (int i = 1; i < parts.Length; i++)
            {
                var child = current.transform.Find(parts[i]);
                if (child == null) return null;
                current = child.gameObject;
            }
            return current;
        }
    }

    #region MonoScript Models

    [Serializable]
    public class MonoScriptParams
    {
        public string operation = "info";
        public string assetPath;          // For info
        public string gameObjectPath;     // For find-component
        public string componentType;      // For find-component
        public string filter;             // For list: filter by name
        public int maxResults;            // For list: max results (default 500)
    }

    [Serializable]
    public class MonoScriptResult
    {
        public bool success;
        public string operation;
        public MonoScriptInfo script;
        public List<MonoScriptInfo> scripts = new List<MonoScriptInfo>();
        public int totalCount;
        public string message;
    }

    [Serializable]
    public class MonoScriptInfo
    {
        public string path;
        public string className;
        public string namespaceName;
        public string fullName;
        public string assemblyName;
        public bool isMonoBehaviour;
        public bool isScriptableObject;
        public bool isEditor;
    }

    #endregion
}

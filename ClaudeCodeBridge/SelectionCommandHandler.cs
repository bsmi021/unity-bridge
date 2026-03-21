using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for setting the Unity Editor selection.
    ///
    /// PURPOSE:
    /// Allows external tools to programmatically select GameObjects in the Editor,
    /// enabling workflows like "select then inspect" or "select then modify".
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "set" - Select one or more GameObjects by path
    /// 2. "clear" - Clear the current selection
    ///
    /// COMMAND JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "set-selection",
    ///   "parametersJson": "{\"operation\":\"set\",\"gameObjectPaths\":[\"Player\",\"Main Camera\"]}"
    /// }
    /// </summary>
    public class SelectionCommandHandler : ICommandHandler
    {
        public string CommandType => "set-selection";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<SetSelectionParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new SetSelectionParams();

                var operation = parameters.operation?.ToLower();
                BridgeLogger.LogDebug($"Executing set-selection: {operation}");

                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Cannot execute while scripts are compiling.");
                }

                switch (operation)
                {
                    case "set":
                        return HandleSet(command, parameters);
                    case "clear":
                        return HandleClear(command);
                    default:
                        return BridgeResponse.Error(command.commandId, command.commandType,
                            $"Unknown operation: {parameters.operation}. Supported: set, clear");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Set-selection error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse HandleSet(BridgeCommand command, SetSelectionParams parameters)
        {
            if (parameters.gameObjectPaths == null || parameters.gameObjectPaths.Count == 0)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "gameObjectPaths is required for set operation.");
            }

            var found = new List<UnityEngine.Object>();
            var notFound = new List<string>();

            foreach (var path in parameters.gameObjectPaths)
            {
                var go = FindGameObjectByPath(path);
                if (go != null)
                    found.Add(go);
                else
                    notFound.Add(path);
            }

            if (found.Count == 0)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"No GameObjects found for paths: {string.Join(", ", notFound)}");
            }

            Selection.objects = found.ToArray();

            var result = new SetSelectionResult
            {
                success = true,
                operation = "set",
                selectedCount = found.Count,
                notFoundCount = notFound.Count,
            };
            foreach (var obj in found)
            {
                var go = obj as GameObject;
                if (go != null)
                    result.selectedPaths.Add(GetGameObjectPath(go));
            }
            foreach (var path in notFound)
                result.notFoundPaths.Add(path);

            BridgeLogger.LogInfo($"Selection set: {found.Count} objects selected");
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse HandleClear(BridgeCommand command)
        {
            Selection.activeGameObject = null;
            Selection.objects = new UnityEngine.Object[0];

            var result = new SetSelectionResult
            {
                success = true,
                operation = "clear",
                selectedCount = 0,
            };

            BridgeLogger.LogInfo("Selection cleared");
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private GameObject FindGameObjectByPath(string path)
        {
            var parts = path.Split('/');
            var rootObjects = SceneManager.GetActiveScene().GetRootGameObjects();
            var current = rootObjects.FirstOrDefault(go => go.name == parts[0]);
            if (current == null)
                return null;

            for (int i = 1; i < parts.Length; i++)
            {
                var child = current.transform.Find(parts[i]);
                if (child == null)
                    return null;
                current = child.gameObject;
            }

            return current;
        }

        private string GetGameObjectPath(GameObject go)
        {
            if (go.transform.parent == null)
                return go.name;
            return $"{GetGameObjectPath(go.transform.parent.gameObject)}/{go.name}";
        }
    }

    #region Set Selection Models

    [Serializable]
    public class SetSelectionParams
    {
        public string operation;
        public List<string> gameObjectPaths = new List<string>();
    }

    [Serializable]
    public class SetSelectionResult
    {
        public bool success;
        public string operation;
        public int selectedCount;
        public int notFoundCount;
        public List<string> selectedPaths = new List<string>();
        public List<string> notFoundPaths = new List<string>();
    }

    #endregion
}

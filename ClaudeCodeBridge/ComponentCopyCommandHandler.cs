using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for copying and pasting component values.
    ///
    /// PURPOSE:
    /// Enables serializing component data to a JSON buffer (copy) and
    /// deserializing it onto another component of the same type (paste).
    /// Uses EditorJsonUtility for full serialization fidelity.
    ///
    /// COMMAND JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "component-copy",
    ///   "parametersJson": "{\"operation\":\"copy\",\"gameObjectPath\":\"Player\",\"componentType\":\"Transform\"}"
    /// }
    /// </summary>
    public class ComponentCopyCommandHandler : ICommandHandler
    {
        public string CommandType => "component-copy";

        // In-memory buffer for copied component data, keyed by component type
        private static readonly Dictionary<string, string> CopyBuffer =
            new Dictionary<string, string>();

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(
                        command.commandId, command.commandType,
                        "Cannot copy/paste components while Unity is compiling.");
                }

                var parameters = JsonUtility.FromJson<ComponentCopyParams>(
                    command.parametersJson ?? "{}");

                if (parameters == null
                    || string.IsNullOrEmpty(parameters.operation))
                {
                    return BridgeResponse.Error(
                        command.commandId, command.commandType,
                        "Missing required parameter: operation");
                }

                ComponentCopyResult result;
                switch (parameters.operation.ToLower())
                {
                    case "copy":
                        result = CopyComponent(parameters);
                        break;
                    case "paste":
                        result = PasteComponent(parameters);
                        break;
                    default:
                        return BridgeResponse.Error(
                            command.commandId, command.commandType,
                            $"Unknown operation: {parameters.operation}. "
                            + "Supported: copy, paste");
                }

                if (result.success)
                {
                    BridgeLogger.LogInfo(result.message);
                    return BridgeResponse.Success(
                        command.commandId, command.commandType,
                        JsonUtility.ToJson(result));
                }
                return BridgeResponse.Error(
                    command.commandId, command.commandType, result.message);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error: {ex}");
                return BridgeResponse.Error(
                    command.commandId, command.commandType, ex.ToString());
            }
        }

        private ComponentCopyResult CopyComponent(ComponentCopyParams parameters)
        {
            var result = new ComponentCopyResult { operation = "copy" };

            if (string.IsNullOrEmpty(parameters.gameObjectPath)
                || string.IsNullOrEmpty(parameters.componentType))
            {
                result.success = false;
                result.message = "gameObjectPath and componentType are required";
                return result;
            }

            var go = FindGameObjectByPath(parameters.gameObjectPath);
            if (go == null)
            {
                result.success = false;
                result.message = $"GameObject not found: {parameters.gameObjectPath}";
                return result;
            }

            var component = FindComponent(go, parameters.componentType);
            if (component == null)
            {
                result.success = false;
                result.message = $"Component not found: {parameters.componentType} "
                    + $"on {parameters.gameObjectPath}";
                return result;
            }

            string json = EditorJsonUtility.ToJson(component, true);
            string typeKey = component.GetType().FullName ?? parameters.componentType;
            CopyBuffer[typeKey] = json;

            result.success = true;
            result.gameObjectPath = parameters.gameObjectPath;
            result.componentType = typeKey;
            result.dataJson = json;
            result.message = $"Copied {typeKey} from {parameters.gameObjectPath}";
            return result;
        }

        private ComponentCopyResult PasteComponent(ComponentCopyParams parameters)
        {
            var result = new ComponentCopyResult { operation = "paste" };

            if (string.IsNullOrEmpty(parameters.gameObjectPath)
                || string.IsNullOrEmpty(parameters.componentType))
            {
                result.success = false;
                result.message = "gameObjectPath and componentType are required";
                return result;
            }

            var go = FindGameObjectByPath(parameters.gameObjectPath);
            if (go == null)
            {
                result.success = false;
                result.message = $"GameObject not found: {parameters.gameObjectPath}";
                return result;
            }

            var component = FindComponent(go, parameters.componentType);
            if (component == null)
            {
                result.success = false;
                result.message = $"Component not found: {parameters.componentType} "
                    + $"on {parameters.gameObjectPath}";
                return result;
            }

            string typeKey = component.GetType().FullName ?? parameters.componentType;

            // Use provided dataJson or fall back to buffer
            string json = parameters.dataJson;
            if (string.IsNullOrEmpty(json))
            {
                if (!CopyBuffer.TryGetValue(typeKey, out json))
                {
                    result.success = false;
                    result.message = $"No copied data for {typeKey}. "
                        + "Copy a component first or provide dataJson.";
                    return result;
                }
            }

            Undo.RecordObject(component, "Paste Component Values");
            EditorJsonUtility.FromJsonOverwrite(json, component);
            EditorUtility.SetDirty(component);

            result.success = true;
            result.gameObjectPath = parameters.gameObjectPath;
            result.componentType = typeKey;
            result.message = $"Pasted {typeKey} onto {parameters.gameObjectPath}";
            return result;
        }

        private Component FindComponent(GameObject go, string typeName)
        {
            foreach (var comp in go.GetComponents<Component>())
            {
                if (comp == null) continue;
                var t = comp.GetType();
                if (t.Name == typeName || t.FullName == typeName)
                    return comp;
            }
            return null;
        }

        private GameObject FindGameObjectByPath(string path)
        {
            var parts = path.Split('/');
            var rootObjects = SceneManager.GetActiveScene().GetRootGameObjects();
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

    [Serializable]
    public class ComponentCopyParams
    {
        public string operation;
        public string gameObjectPath;
        public string componentType;
        public string dataJson;
    }

    [Serializable]
    public class ComponentCopyResult
    {
        public string operation;
        public string gameObjectPath;
        public string componentType;
        public string dataJson;
        public bool success;
        public string message;
    }
}

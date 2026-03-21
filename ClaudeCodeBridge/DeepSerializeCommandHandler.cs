using System;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for EditorJsonUtility deep serialization.
    /// Provides full Editor serialization including private [SerializeField] fields.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "get" - Serialize a component using EditorJsonUtility.ToJson
    /// 2. "set" - Overwrite a component from JSON using EditorJsonUtility.FromJsonOverwrite
    /// </summary>
    public class DeepSerializeCommandHandler : ICommandHandler
    {
        public string CommandType => "deep-serialize";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<DeepSerializeParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new DeepSerializeParams();

                var operation = parameters.operation?.ToLower() ?? "get";
                BridgeLogger.LogDebug($"Executing deep-serialize: {operation}");

                switch (operation)
                {
                    case "get":
                        return HandleGet(command, parameters);
                    case "set":
                        return HandleSet(command, parameters);
                    default:
                        return BridgeResponse.Error(command.commandId, command.commandType,
                            $"Unknown operation: {parameters.operation}. " +
                            "Supported: get, set");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Deep-serialize error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse HandleGet(BridgeCommand command, DeepSerializeParams p)
        {
            if (string.IsNullOrEmpty(p.gameObjectPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "gameObjectPath is required for get operation.");
            }
            if (string.IsNullOrEmpty(p.componentType))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "componentType is required for get operation.");
            }

            var go = FindGameObjectByPath(p.gameObjectPath);
            if (go == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"GameObject not found: {p.gameObjectPath}");
            }

            var component = FindComponent(go, p.componentType);
            if (component == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Component not found: {p.componentType} on {p.gameObjectPath}");
            }

            bool prettyPrint = p.prettyPrint;
            string json = EditorJsonUtility.ToJson(component, prettyPrint);

            var result = new DeepSerializeResult
            {
                success = true,
                operation = "get",
                gameObjectPath = p.gameObjectPath,
                componentType = component.GetType().FullName,
                json = json,
                message = $"Serialized {p.componentType} ({json.Length} chars)",
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse HandleSet(BridgeCommand command, DeepSerializeParams p)
        {
            if (string.IsNullOrEmpty(p.gameObjectPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "gameObjectPath is required for set operation.");
            }
            if (string.IsNullOrEmpty(p.componentType))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "componentType is required for set operation.");
            }
            if (string.IsNullOrEmpty(p.json))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "json is required for set operation.");
            }

            if (EditorApplication.isPlaying)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "Cannot overwrite components during play mode.");
            }

            var go = FindGameObjectByPath(p.gameObjectPath);
            if (go == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"GameObject not found: {p.gameObjectPath}");
            }

            var component = FindComponent(go, p.componentType);
            if (component == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Component not found: {p.componentType} on {p.gameObjectPath}");
            }

            Undo.RecordObject(component, $"Deep serialize overwrite {p.componentType}");
            EditorJsonUtility.FromJsonOverwrite(p.json, component);
            EditorUtility.SetDirty(component);

            var result = new DeepSerializeResult
            {
                success = true,
                operation = "set",
                gameObjectPath = p.gameObjectPath,
                componentType = component.GetType().FullName,
                message = $"Overwrote {p.componentType} from JSON",
            };
            BridgeLogger.LogInfo($"Deep serialize overwrite: {p.componentType}");
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private static GameObject FindGameObjectByPath(string path)
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

        private static Component FindComponent(GameObject go, string typeName)
        {
            return go.GetComponents<Component>().FirstOrDefault(c =>
                c is not null &&
                (c.GetType().Name == typeName || c.GetType().FullName == typeName));
        }
    }

    #region Deep Serialize Models

    [Serializable]
    public class DeepSerializeParams
    {
        public string operation = "get";
        public string gameObjectPath;
        public string componentType;
        public string json;              // For set operation
        public bool prettyPrint = true;
    }

    [Serializable]
    public class DeepSerializeResult
    {
        public bool success;
        public string operation;
        public string gameObjectPath;
        public string componentType;
        public string json;
        public string message;
    }

    #endregion
}

using System;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for removing a component from a GameObject.
    ///
    /// PURPOSE:
    /// Removes a component by type from a specified GameObject with undo support.
    /// Cannot remove Transform (every GO requires one).
    ///
    /// COMMAND JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "remove-component",
    ///   "parametersJson": "{\"gameObjectPath\":\"Player\",\"componentType\":\"Rigidbody\"}"
    /// }
    /// </summary>
    public class RemoveComponentCommandHandler : ICommandHandler
    {
        public string CommandType => "remove-component";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(
                        command.commandId, command.commandType,
                        "Cannot remove component while Unity is compiling.");
                }

                var parameters = JsonUtility.FromJson<RemoveComponentParams>(
                    command.parametersJson ?? "{}");

                if (parameters == null
                    || string.IsNullOrEmpty(parameters.gameObjectPath)
                    || string.IsNullOrEmpty(parameters.componentType))
                {
                    return BridgeResponse.Error(
                        command.commandId, command.commandType,
                        "Missing required parameters: gameObjectPath and componentType");
                }

                // Reject Transform removal
                if (parameters.componentType.Equals("Transform", StringComparison.OrdinalIgnoreCase))
                {
                    return BridgeResponse.Error(
                        command.commandId, command.commandType,
                        "Cannot remove Transform component.");
                }

                var go = FindGameObjectByPath(parameters.gameObjectPath);
                if (go == null)
                {
                    return BridgeResponse.Error(
                        command.commandId, command.commandType,
                        $"GameObject not found: {parameters.gameObjectPath}");
                }

                var component = FindComponent(go, parameters.componentType);
                if (component == null)
                {
                    return BridgeResponse.Error(
                        command.commandId, command.commandType,
                        $"Component not found: {parameters.componentType} on {parameters.gameObjectPath}");
                }

                Undo.DestroyObjectImmediate(component);

                EditorUtility.SetDirty(go);
                UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(go.scene);

                var result = new RemoveComponentResult
                {
                    success = true,
                    gameObjectPath = parameters.gameObjectPath,
                    componentType = parameters.componentType,
                    message = $"Removed {parameters.componentType} from {parameters.gameObjectPath}",
                };

                BridgeLogger.LogInfo(result.message);
                return BridgeResponse.Success(
                    command.commandId, command.commandType, JsonUtility.ToJson(result));
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
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
    public class RemoveComponentParams
    {
        public string gameObjectPath;
        public string componentType;
    }

    [Serializable]
    public class RemoveComponentResult
    {
        public bool success;
        public string gameObjectPath;
        public string componentType;
        public string message;
    }
}

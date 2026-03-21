using System;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for enabling/disabling components on a GameObject.
    ///
    /// PURPOSE:
    /// Toggles the enabled state of Behaviour, Renderer, and Collider components.
    /// Uses Undo.RecordObject for undo support.
    ///
    /// COMMAND JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "component-toggle",
    ///   "parametersJson": "{\"gameObjectPath\":\"Player\",\"componentType\":\"MeshRenderer\",\"enabled\":false}"
    /// }
    /// </summary>
    public class ComponentToggleCommandHandler : ICommandHandler
    {
        public string CommandType => "component-toggle";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(
                        command.commandId, command.commandType,
                        "Cannot toggle component while Unity is compiling.");
                }

                var parameters = JsonUtility.FromJson<ComponentToggleParams>(
                    command.parametersJson ?? "{}");

                if (parameters == null
                    || string.IsNullOrEmpty(parameters.gameObjectPath)
                    || string.IsNullOrEmpty(parameters.componentType))
                {
                    return BridgeResponse.Error(
                        command.commandId, command.commandType,
                        "Missing required parameters: gameObjectPath and componentType");
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

                bool toggled = TryToggle(component, parameters.enabled);
                if (!toggled)
                {
                    return BridgeResponse.Error(
                        command.commandId, command.commandType,
                        $"Component {parameters.componentType} does not support enable/disable. "
                        + "Only Behaviour, Renderer, and Collider subclasses can be toggled.");
                }

                EditorUtility.SetDirty(component);
                UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(go.scene);

                var result = new ComponentToggleResult
                {
                    success = true,
                    gameObjectPath = parameters.gameObjectPath,
                    componentType = parameters.componentType,
                    enabled = parameters.enabled,
                    message = $"Set {parameters.componentType} enabled={parameters.enabled}",
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

        /// <summary>
        /// Attempt to toggle enabled state. Returns false if component type
        /// does not support enabled property.
        /// </summary>
        private bool TryToggle(Component component, bool enabled)
        {
            Undo.RecordObject(component, "Toggle Component");

            if (component is Behaviour behaviour)
            {
                behaviour.enabled = enabled;
                return true;
            }
            if (component is Renderer renderer)
            {
                renderer.enabled = enabled;
                return true;
            }
            if (component is Collider collider)
            {
                collider.enabled = enabled;
                return true;
            }
            return false;
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
    public class ComponentToggleParams
    {
        public string gameObjectPath;
        public string componentType;
        public bool enabled;
    }

    [Serializable]
    public class ComponentToggleResult
    {
        public bool success;
        public string gameObjectPath;
        public string componentType;
        public bool enabled;
        public string message;
    }
}

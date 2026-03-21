using System;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for resetting a component to its default values.
    ///
    /// PURPOSE:
    /// Resets a component's serialized fields to defaults. Uses
    /// Unsupported.SmartReset when available (preferred), or creates
    /// a temporary default instance and copies values via EditorJsonUtility.
    ///
    /// COMMAND JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "component-reset",
    ///   "parametersJson": "{\"gameObjectPath\":\"Player\",\"componentType\":\"BoxCollider\"}"
    /// }
    /// </summary>
    public class ComponentResetCommandHandler : ICommandHandler
    {
        public string CommandType => "component-reset";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(
                        command.commandId, command.commandType,
                        "Cannot reset component while Unity is compiling.");
                }

                var parameters = JsonUtility.FromJson<ComponentResetParams>(
                    command.parametersJson ?? "{}");

                if (parameters == null
                    || string.IsNullOrEmpty(parameters.gameObjectPath)
                    || string.IsNullOrEmpty(parameters.componentType))
                {
                    return BridgeResponse.Error(
                        command.commandId, command.commandType,
                        "gameObjectPath and componentType are required");
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
                        $"Component not found: {parameters.componentType} "
                        + $"on {parameters.gameObjectPath}");
                }

                Undo.RecordObject(component, "Reset Component");
                ResetToDefaults(component);
                EditorUtility.SetDirty(component);

                var result = new ComponentResetResult
                {
                    success = true,
                    gameObjectPath = parameters.gameObjectPath,
                    componentType = parameters.componentType,
                    message = $"Reset {parameters.componentType} to defaults",
                };

                BridgeLogger.LogInfo(result.message);
                return BridgeResponse.Success(
                    command.commandId, command.commandType,
                    JsonUtility.ToJson(result));
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error: {ex}");
                return BridgeResponse.Error(
                    command.commandId, command.commandType, ex.ToString());
            }
        }

        /// <summary>
        /// Reset component to default values. Tries SmartReset first via
        /// reflection (internal API), falls back to EditorJsonUtility copy.
        /// </summary>
        private void ResetToDefaults(Component component)
        {
            // Try Unsupported.SmartReset via reflection
            var unsupportedType = typeof(EditorApplication).Assembly
                .GetType("UnityEditor.Unsupported");

            if (unsupportedType != null)
            {
                var smartReset = unsupportedType.GetMethod(
                    "SmartReset",
                    System.Reflection.BindingFlags.Static
                    | System.Reflection.BindingFlags.Public);

                if (smartReset != null)
                {
                    smartReset.Invoke(null, new object[] { component });
                    BridgeLogger.LogDebug("Used SmartReset for component reset");
                    return;
                }
            }

            // Fallback: create temporary object, add component, copy defaults
            FallbackResetViaTemp(component);
        }

        /// <summary>
        /// Fallback reset by creating a temp GameObject, adding the same
        /// component type, and copying its default values via JSON.
        /// </summary>
        private void FallbackResetViaTemp(Component component)
        {
            var compType = component.GetType();
            var tempGo = new GameObject("__reset_temp__");
            tempGo.hideFlags = HideFlags.HideAndDontSave;

            try
            {
                // Transform cannot be re-added; handle specially
                if (compType == typeof(Transform))
                {
                    var tempTransform = tempGo.transform;
                    string json = EditorJsonUtility.ToJson(tempTransform, false);
                    EditorJsonUtility.FromJsonOverwrite(json, component);
                    return;
                }

                var tempComponent = tempGo.AddComponent(compType);
                if (tempComponent != null)
                {
                    string json = EditorJsonUtility.ToJson(tempComponent, false);
                    EditorJsonUtility.FromJsonOverwrite(json, component);
                }
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(tempGo);
            }

            BridgeLogger.LogDebug("Used fallback temp-object reset");
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
    public class ComponentResetParams
    {
        public string gameObjectPath;
        public string componentType;
    }

    [Serializable]
    public class ComponentResetResult
    {
        public bool success;
        public string gameObjectPath;
        public string componentType;
        public string message;
    }
}

using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for SerializedProperty-based component access.
    ///
    /// PURPOSE:
    /// Provides access to ALL serialized fields including [SerializeField] private
    /// fields that reflection-based approaches miss. Uses Unity's SerializedObject
    /// and SerializedProperty APIs — the same mechanism the Inspector uses.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "list" - Enumerate all serialized properties on a component
    /// 2. "get" - Get a single property value by path
    /// 3. "set" - Set a single property value by path (with Undo)
    ///
    /// GUARDS:
    /// - EditorApplication.isCompiling: blocks all operations
    /// - EditorApplication.isPlaying: blocks set operations
    /// </summary>
    public class SerializedPropertyCommandHandler : ICommandHandler
    {
        public string CommandType => "serialized-property";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Cannot access properties while scripts are compiling.");
                }

                var parameters = JsonUtility.FromJson<SerializedPropertyParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new SerializedPropertyParams();

                SerializedPropertyResult result;
                switch (parameters.operation?.ToLower())
                {
                    case "list":
                        result = ExecuteList(parameters);
                        break;
                    case "get":
                        result = ExecuteGet(parameters);
                        break;
                    case "set":
                        result = ExecuteSet(parameters);
                        break;
                    default:
                        result = new SerializedPropertyResult
                        {
                            success = false,
                            operation = parameters.operation,
                            message = $"Unknown operation: {parameters.operation}. "
                                + "Supported: list, get, set"
                        };
                        break;
                }

                var resultJson = JsonUtility.ToJson(result);
                return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"SerializedProperty error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private SerializedPropertyResult ExecuteList(SerializedPropertyParams parameters)
        {
            var component = FindComponent(parameters);
            if (component == null)
                return ComponentNotFoundResult("list", parameters);

            var so = new SerializedObject(component);
            var result = new SerializedPropertyResult
            {
                success = true,
                operation = "list",
                gameObjectPath = parameters.gameObjectPath,
                componentType = parameters.componentType
            };

            var iterator = so.GetIterator();
            bool enterChildren = true;
            while (iterator.NextVisible(enterChildren))
            {
                enterChildren = false;
                if (iterator.name == "m_Script") continue;

                result.properties.Add(BuildPropertyInfo(iterator));
            }

            result.message = $"Found {result.properties.Count} serialized properties";
            return result;
        }

        private SerializedPropertyResult ExecuteGet(SerializedPropertyParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.propertyPath))
                return ErrorResult("get", "propertyPath is required for get operation");

            var component = FindComponent(parameters);
            if (component == null)
                return ComponentNotFoundResult("get", parameters);

            var so = new SerializedObject(component);
            var prop = so.FindProperty(parameters.propertyPath);
            if (prop == null)
            {
                return ErrorResult("get",
                    $"Property not found: {parameters.propertyPath}");
            }

            var result = new SerializedPropertyResult
            {
                success = true,
                operation = "get",
                gameObjectPath = parameters.gameObjectPath,
                componentType = parameters.componentType
            };
            result.properties.Add(BuildPropertyInfo(prop));
            result.message = $"Retrieved property: {parameters.propertyPath}";
            return result;
        }

        private SerializedPropertyResult ExecuteSet(SerializedPropertyParams parameters)
        {
            if (EditorApplication.isPlaying)
                return ErrorResult("set", "Cannot set properties in play mode.");

            if (string.IsNullOrEmpty(parameters.propertyPath))
                return ErrorResult("set", "propertyPath is required for set operation");

            if (string.IsNullOrEmpty(parameters.valueJson))
                return ErrorResult("set", "valueJson is required for set operation");

            var component = FindComponent(parameters);
            if (component == null)
                return ComponentNotFoundResult("set", parameters);

            var so = new SerializedObject(component);
            var prop = so.FindProperty(parameters.propertyPath);
            if (prop == null)
                return ErrorResult("set", $"Property not found: {parameters.propertyPath}");

            bool applied = SerializedPropertyHelpers.SetPropertyValue(prop, parameters.valueJson);
            if (!applied)
                return ErrorResult("set", $"Failed to set value for type: {prop.propertyType}");

            so.ApplyModifiedProperties();

            var result = new SerializedPropertyResult
            {
                success = true,
                operation = "set",
                gameObjectPath = parameters.gameObjectPath,
                componentType = parameters.componentType
            };
            // Re-read the property to confirm
            so.Update();
            var updatedProp = so.FindProperty(parameters.propertyPath);
            if (updatedProp != null)
                result.properties.Add(BuildPropertyInfo(updatedProp));

            result.message = $"Property {parameters.propertyPath} updated successfully";
            return result;
        }

        // -----------------------------------------------------------------
        // Helpers
        // -----------------------------------------------------------------

        private SerializedPropertyInfo BuildPropertyInfo(SerializedProperty prop)
        {
            return new SerializedPropertyInfo
            {
                name = prop.name,
                path = prop.propertyPath,
                displayName = prop.displayName,
                type = prop.propertyType.ToString(),
                value = SerializedPropertyHelpers.GetPropertyValueString(prop),
                depth = prop.depth,
                isExpanded = prop.isExpanded,
                isArray = prop.isArray,
                arraySize = prop.isArray ? prop.arraySize : -1
            };
        }

        private Component FindComponent(SerializedPropertyParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.gameObjectPath)
                || string.IsNullOrEmpty(parameters.componentType))
                return null;

            var go = FindGameObjectByPath(parameters.gameObjectPath);
            if (go == null) return null;

            var components = go.GetComponents<Component>();
            return components.FirstOrDefault(c =>
                c != null && (
                    c.GetType().Name == parameters.componentType
                    || c.GetType().FullName == parameters.componentType
                )
            );
        }

        private SerializedPropertyResult ComponentNotFoundResult(
            string operation, SerializedPropertyParams parameters)
        {
            return ErrorResult(operation,
                $"Component '{parameters.componentType}' not found on '{parameters.gameObjectPath}'");
        }

        private SerializedPropertyResult ErrorResult(string operation, string message)
        {
            return new SerializedPropertyResult
            {
                success = false,
                operation = operation,
                message = message
            };
        }

        private GameObject FindGameObjectByPath(string path)
        {
            if (string.IsNullOrEmpty(path)) return null;

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
}

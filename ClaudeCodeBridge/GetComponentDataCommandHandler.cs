using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for reading component data from GameObjects.
    ///
    /// PURPOSE:
    /// Reads serialized field values from Unity components, enabling inspection
    /// of GameObject state without manually opening the Inspector. Critical for
    /// automated testing, debugging, and validation workflows.
    ///
    /// USE CASES:
    /// - Verify component configuration after scene changes
    /// - Read runtime state for debugging
    /// - Extract configuration values for documentation
    /// - Validate data-driven content
    /// - Compare expected vs actual component values in tests
    ///
    /// COMMAND JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "get-component-data",
    ///   "timestamp": "2025-10-05T18:00:00Z",
    ///   "parametersJson": "{\"gameObjectPath\":\"Player\",\"componentType\":\"BWS.CharacterStats\",\"fieldNames\":[\"maxHealth\",\"currentHealth\"]}"
    /// }
    ///
    /// USAGE EXAMPLES:
    ///
    /// 1. Read all fields from a component:
    ///    send-command.ps1 -CommandType "get-component-data" -Parameters @{gameObjectPath="Player"; componentType="BWS.CharacterStats"}
    ///
    /// 2. Read specific fields only:
    ///    send-command.ps1 -CommandType "get-component-data" -Parameters @{gameObjectPath="Player"; componentType="Transform"; fieldNames=@("position","rotation")}
    ///
    /// 3. Read from nested object:
    ///    send-command.ps1 -CommandType "get-component-data" -Parameters @{gameObjectPath="Player/Camera"; componentType="UnityEngine.Camera"}
    /// </summary>
    public class GetComponentDataCommandHandler : ICommandHandler
    {
        public string CommandType => "get-component-data";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<GetComponentDataParams>(command.parametersJson ?? "{}");
                if (parameters == null || string.IsNullOrEmpty(parameters.gameObjectPath) || string.IsNullOrEmpty(parameters.componentType))
                {
                    return BridgeResponse.Error(command.commandId, command.commandType, "Missing required parameters: gameObjectPath and componentType");
                }

                BridgeLogger.LogDebug($"Reading data from {parameters.gameObjectPath}::{parameters.componentType}");

                // Find GameObject
                var gameObject = FindGameObjectByPath(parameters.gameObjectPath);
                if (gameObject == null)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType, $"GameObject not found: {parameters.gameObjectPath}");
                }

                // Find component
                var component = FindComponent(gameObject, parameters.componentType);
                if (component == null)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType, $"Component not found: {parameters.componentType} on {parameters.gameObjectPath}");
                }

                // Build result
                var result = new GetComponentDataResult
                {
                    gameObjectPath = parameters.gameObjectPath,
                    componentType = parameters.componentType
                };

                // Get fields
                var componentType = component.GetType();
                var fields = componentType.GetFields(BindingFlags.Public | BindingFlags.Instance);

                foreach (var field in fields)
                {
                    // Filter by requested field names if specified
                    if (parameters.fieldNames.Count > 0 && !parameters.fieldNames.Contains(field.Name))
                        continue;

                    var fieldInfo = new ComponentFieldInfo
                    {
                        name = field.Name,
                        type = field.FieldType.FullName,
                        value = SerializeFieldValue(field.GetValue(component))
                    };
                    result.fields.Add(fieldInfo);
                }

                var resultJson = JsonUtility.ToJson(result);
                BridgeLogger.LogInfo($"Read {result.fields.Count} fields");

                return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        /// <summary>
        /// Find GameObject by hierarchy path.
        /// </summary>
        private GameObject FindGameObjectByPath(string path)
        {
            var parts = path.Split('/');
            GameObject current = null;

            // Find root object
            var rootObjects = SceneManager.GetActiveScene().GetRootGameObjects();
            current = rootObjects.FirstOrDefault(go => go.name == parts[0]);
            if (current == null)
                return null;

            // Traverse hierarchy
            for (int i = 1; i < parts.Length; i++)
            {
                var child = current.transform.Find(parts[i]);
                if (child == null)
                    return null;
                current = child.gameObject;
            }

            return current;
        }

        /// <summary>
        /// Find component by type name (supports short names and full names).
        /// </summary>
        private Component FindComponent(GameObject go, string typeName)
        {
            var components = go.GetComponents<Component>();
            return components.FirstOrDefault(c =>
                c.GetType().Name == typeName ||
                c.GetType().FullName == typeName
            );
        }

        /// <summary>
        /// Serialize field value to JSON string.
        /// </summary>
        private string SerializeFieldValue(object value)
        {
            if (value == null)
                return "null";

            try
            {
                // Handle Unity types
                if (value is Vector3 v3)
                    return JsonUtility.ToJson(v3);
                if (value is Vector2 v2)
                    return JsonUtility.ToJson(v2);
                if (value is Quaternion q)
                    return JsonUtility.ToJson(q);
                if (value is Color c)
                    return JsonUtility.ToJson(c);

                // Handle primitives and strings
                if (value is string || value.GetType().IsPrimitive)
                    return value.ToString();

                // Try JsonUtility for other types
                return JsonUtility.ToJson(value);
            }
            catch
            {
                return value.ToString();
            }
        }
    }
}

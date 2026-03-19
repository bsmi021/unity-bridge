using System;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for modifying component data on GameObjects.
    ///
    /// PURPOSE:
    /// Modifies serialized field values on Unity components programmatically.
    /// Enables automated setup, testing, and configuration of GameObjects
    /// without manual Inspector manipulation.
    ///
    /// USE CASES:
    /// - Automated test setup (set health, position, etc.)
    /// - Batch configuration of multiple objects
    /// - Programmatic scene setup for specific scenarios
    /// - Test data injection
    /// - Quick iteration on component values during development
    ///
    /// COMMAND JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "set-component-data",
    ///   "timestamp": "2025-10-05T18:00:00Z",
    ///   "parametersJson": "{\"gameObjectPath\":\"Player\",\"componentType\":\"BWS.CharacterStats\",\"fieldUpdates\":[{\"fieldName\":\"maxHealth\",\"valueJson\":\"100\"},{\"fieldName\":\"currentHealth\",\"valueJson\":\"50\"}]}"
    /// }
    ///
    /// USAGE EXAMPLES:
    ///
    /// 1. Set single field:
    ///    send-command.ps1 -CommandType "set-component-data" -Parameters @{gameObjectPath="Player"; componentType="BWS.CharacterStats"; fieldUpdates=@(@{fieldName="maxHealth"; valueJson="150"})}
    ///
    /// 2. Set multiple fields:
    ///    send-command.ps1 -CommandType "set-component-data" -Parameters @{gameObjectPath="Player"; componentType="Transform"; fieldUpdates=@(@{fieldName="position"; valueJson='{"x":0,"y":1,"z":0}'})}
    ///
    /// 3. Set nested object field:
    ///    send-command.ps1 -CommandType "set-component-data" -Parameters @{gameObjectPath="Player/Camera"; componentType="Camera"; fieldUpdates=@(@{fieldName="fieldOfView"; valueJson="90"})}
    ///
    /// NOTE: This command marks the scene as dirty to ensure changes are saved.
    /// </summary>
    public class SetComponentDataCommandHandler : ICommandHandler
    {
        public string CommandType => "set-component-data";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<SetComponentDataParams>(command.parametersJson ?? "{}");
                if (parameters == null || string.IsNullOrEmpty(parameters.gameObjectPath) || string.IsNullOrEmpty(parameters.componentType))
                {
                    return BridgeResponse.Error(command.commandId, command.commandType, "Missing required parameters: gameObjectPath and componentType");
                }

                BridgeLogger.LogDebug($"Setting data on {parameters.gameObjectPath}::{parameters.componentType}");

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

                // Apply field updates
                var result = new SetComponentDataResult
                {
                    gameObjectPath = parameters.gameObjectPath,
                    componentType = parameters.componentType
                };

                foreach (var fieldUpdate in parameters.fieldUpdates)
                {
                    try
                    {
                        var field = component.GetType().GetField(fieldUpdate.fieldName, BindingFlags.Public | BindingFlags.Instance);
                        if (field == null)
                        {
                            BridgeLogger.LogWarning($"Field not found: {fieldUpdate.fieldName}");
                            continue;
                        }

                        var value = DeserializeFieldValue(fieldUpdate.valueJson, field.FieldType);
                        field.SetValue(component, value);
                        result.updatedFields.Add(fieldUpdate.fieldName);
                        result.fieldsUpdated++;

                        BridgeLogger.LogDebug($"Set {fieldUpdate.fieldName} = {fieldUpdate.valueJson}");
                    }
                    catch (Exception ex)
                    {
                        BridgeLogger.LogError($"Error setting field {fieldUpdate.fieldName}: {ex.Message}");
                    }
                }

                // Mark scene dirty
                if (result.fieldsUpdated > 0)
                {
                    EditorUtility.SetDirty(component);
                    UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(gameObject.scene);
                }

                var resultJson = JsonUtility.ToJson(result);
                BridgeLogger.LogInfo($"Updated {result.fieldsUpdated} fields");

                return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private GameObject FindGameObjectByPath(string path)
        {
            var parts = path.Split('/');
            GameObject current = null;

            var rootObjects = SceneManager.GetActiveScene().GetRootGameObjects();
            current = rootObjects.FirstOrDefault(go => go.name == parts[0]);
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

        private Component FindComponent(GameObject go, string typeName)
        {
            var components = go.GetComponents<Component>();
            return components.FirstOrDefault(c =>
                c.GetType().Name == typeName ||
                c.GetType().FullName == typeName
            );
        }

        /// <summary>
        /// Deserialize JSON value to field type.
        /// </summary>
        private object DeserializeFieldValue(string valueJson, Type fieldType)
        {
            if (string.IsNullOrEmpty(valueJson) || valueJson == "null")
                return null;

            try
            {
                // Handle primitives
                if (fieldType == typeof(int))
                    return int.Parse(valueJson);
                if (fieldType == typeof(float))
                    return float.Parse(valueJson);
                if (fieldType == typeof(double))
                    return double.Parse(valueJson);
                if (fieldType == typeof(bool))
                    return bool.Parse(valueJson);
                if (fieldType == typeof(string))
                    return valueJson.Trim('"');

                // Handle Unity types with JsonUtility
                if (fieldType == typeof(Vector3) || fieldType == typeof(Vector2) ||
                    fieldType == typeof(Quaternion) || fieldType == typeof(Color))
                {
                    return JsonUtility.FromJson(valueJson, fieldType);
                }

                // Try generic JsonUtility deserialization
                return JsonUtility.FromJson(valueJson, fieldType);
            }
            catch (Exception ex)
            {
                throw new Exception($"Failed to deserialize value '{valueJson}' to type {fieldType.Name}: {ex.Message}");
            }
        }
    }
}

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
    /// Uses SerializedObject/SerializedProperty as the PRIMARY approach (works
    /// with [SerializeField] private fields). Falls back to reflection only
    /// for runtime-only fields not visible to serialization.
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
                var parameters = JsonUtility.FromJson<SetComponentDataParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null
                    || string.IsNullOrEmpty(parameters.gameObjectPath)
                    || string.IsNullOrEmpty(parameters.componentType))
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Missing required parameters: gameObjectPath and componentType");
                }

                BridgeLogger.LogDebug(
                    $"Setting data on {parameters.gameObjectPath}::{parameters.componentType}");

                var gameObject = FindGameObjectByPath(parameters.gameObjectPath);
                if (gameObject == null)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        $"GameObject not found: {parameters.gameObjectPath}");
                }

                var component = FindComponent(gameObject, parameters.componentType);
                if (component == null)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        $"Component not found: {parameters.componentType} "
                        + $"on {parameters.gameObjectPath}");
                }

                var result = new SetComponentDataResult
                {
                    gameObjectPath = parameters.gameObjectPath,
                    componentType = parameters.componentType
                };

                // Primary: use SerializedObject (works with private [SerializeField])
                var so = new SerializedObject(component);
                foreach (var fieldUpdate in parameters.fieldUpdates)
                {
                    bool updated = TrySetViaSerializedProperty(so, fieldUpdate);
                    if (!updated)
                    {
                        // Fallback: reflection for runtime-only fields
                        updated = TrySetViaReflection(component, fieldUpdate);
                    }

                    if (updated)
                    {
                        result.updatedFields.Add(fieldUpdate.fieldName);
                        result.fieldsUpdated++;
                        BridgeLogger.LogDebug(
                            $"Set {fieldUpdate.fieldName} = {fieldUpdate.valueJson}");
                    }
                    else
                    {
                        BridgeLogger.LogWarning(
                            $"Field not found or unsupported: {fieldUpdate.fieldName}");
                    }
                }

                // Mark scene dirty
                if (result.fieldsUpdated > 0)
                {
                    EditorUtility.SetDirty(component);
                    UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(
                        gameObject.scene);
                }

                var resultJson = JsonUtility.ToJson(result);
                BridgeLogger.LogInfo($"Updated {result.fieldsUpdated} fields");
                return BridgeResponse.Success(
                    command.commandId, command.commandType, resultJson);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error: {ex}");
                return BridgeResponse.Error(
                    command.commandId, command.commandType, ex.ToString());
            }
        }

        /// <summary>
        /// Try to set a field value using SerializedObject/SerializedProperty.
        /// This is the CORRECT way to modify Unity components — works with
        /// private [SerializeField] fields and records proper Undo.
        /// </summary>
        private bool TrySetViaSerializedProperty(SerializedObject so, FieldUpdate update)
        {
            try
            {
                var prop = so.FindProperty(update.fieldName);
                if (prop == null) return false;

                bool set = SerializedPropertyHelpers.SetPropertyValue(prop, update.valueJson);
                if (set)
                    so.ApplyModifiedProperties();
                return set;
            }
            catch (Exception ex)
            {
                BridgeLogger.LogWarning(
                    $"SerializedProperty set failed for {update.fieldName}: {ex.Message}");
                return false;
            }
        }

        /// <summary>
        /// Fallback: set field via reflection for runtime-only fields not
        /// visible to Unity serialization.
        /// </summary>
        private bool TrySetViaReflection(Component component, FieldUpdate update)
        {
            try
            {
                var field = component.GetType().GetField(
                    update.fieldName,
                    BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                if (field == null) return false;

                var value = DeserializeFieldValue(update.valueJson, field.FieldType);
                Undo.RecordObject(component, $"Set {update.fieldName}");
                field.SetValue(component, value);
                return true;
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError(
                    $"Reflection set failed for {update.fieldName}: {ex.Message}");
                return false;
            }
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

        private Component FindComponent(GameObject go, string typeName)
        {
            var components = go.GetComponents<Component>();
            return components.FirstOrDefault(c =>
                c.GetType().Name == typeName
                || c.GetType().FullName == typeName
            );
        }

        private object DeserializeFieldValue(string valueJson, Type fieldType)
        {
            if (string.IsNullOrEmpty(valueJson) || valueJson == "null")
                return null;

            if (fieldType == typeof(int)) return int.Parse(valueJson);
            if (fieldType == typeof(float)) return float.Parse(valueJson);
            if (fieldType == typeof(double)) return double.Parse(valueJson);
            if (fieldType == typeof(bool)) return bool.Parse(valueJson);
            if (fieldType == typeof(string)) return valueJson.Trim('"');

            if (fieldType == typeof(Vector3) || fieldType == typeof(Vector2)
                || fieldType == typeof(Quaternion) || fieldType == typeof(Color))
            {
                return JsonUtility.FromJson(valueJson, fieldType);
            }

            return JsonUtility.FromJson(valueJson, fieldType);
        }
    }
}

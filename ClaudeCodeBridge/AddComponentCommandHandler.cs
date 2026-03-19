using System;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for adding components to GameObjects.
    ///
    /// PURPOSE:
    /// Dynamically adds Unity components to GameObjects at runtime or in edit mode.
    /// Enables programmatic GameObject composition, automated test setup, and
    /// rapid prototyping without manual Inspector work.
    ///
    /// USE CASES:
    /// - Add components for test scenarios (e.g., add Rigidbody for physics tests)
    /// - Automated GameObject setup from scripts
    /// - Batch component addition across multiple objects
    /// - Programmatic prefab configuration
    /// - Rapid prototyping and iteration
    ///
    /// COMMAND JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "add-component",
    ///   "timestamp": "2025-10-05T18:00:00Z",
    ///   "parametersJson": "{\"gameObjectPath\":\"Player\",\"componentType\":\"UnityEngine.Rigidbody\"}"
    /// }
    ///
    /// USAGE EXAMPLES:
    ///
    /// 1. Add Unity component:
    ///    send-command.ps1 -CommandType "add-component" -Parameters @{gameObjectPath="Player"; componentType="UnityEngine.Rigidbody"}
    ///
    /// 2. Add custom component:
    ///    send-command.ps1 -CommandType "add-component" -Parameters @{gameObjectPath="Enemy"; componentType="BWS.CharacterStats"}
    ///
    /// 3. Add to nested object:
    ///    send-command.ps1 -CommandType "add-component" -Parameters @{gameObjectPath="Player/Camera"; componentType="UnityEngine.AudioListener"}
    ///
    /// NOTE: Component must be a valid Unity component type. Duplicate components
    /// (except Transform) will not be added if they already exist.
    /// </summary>
    public class AddComponentCommandHandler : ICommandHandler
    {
        public string CommandType => "add-component";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<AddComponentParams>(command.parametersJson ?? "{}");
                if (parameters == null || string.IsNullOrEmpty(parameters.gameObjectPath) || string.IsNullOrEmpty(parameters.componentType))
                {
                    return BridgeResponse.Error(command.commandId, command.commandType, "Missing required parameters: gameObjectPath and componentType");
                }

                BridgeLogger.LogDebug($"Adding {parameters.componentType} to {parameters.gameObjectPath}");

                // Find GameObject
                var gameObject = FindGameObjectByPath(parameters.gameObjectPath);
                if (gameObject == null)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType, $"GameObject not found: {parameters.gameObjectPath}");
                }

                // Find component type
                var componentType = FindComponentType(parameters.componentType);
                if (componentType == null)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType, $"Component type not found: {parameters.componentType}");
                }

                // Check if component already exists (except for components that allow duplicates)
                if (gameObject.GetComponent(componentType) != null && !AllowsDuplicates(componentType))
                {
                    var result = new AddComponentResult
                    {
                        gameObjectPath = parameters.gameObjectPath,
                        componentType = parameters.componentType,
                        success = false,
                        message = $"Component already exists on GameObject: {parameters.componentType}"
                    };
                    return BridgeResponse.Success(command.commandId, command.commandType, JsonUtility.ToJson(result));
                }

                // Add component
                var addedComponent = gameObject.AddComponent(componentType);
                if (addedComponent == null)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType, $"Failed to add component: {parameters.componentType}");
                }

                // Mark scene dirty
                EditorUtility.SetDirty(gameObject);
                UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(gameObject.scene);

                var successResult = new AddComponentResult
                {
                    gameObjectPath = parameters.gameObjectPath,
                    componentType = parameters.componentType,
                    success = true,
                    message = $"Successfully added {parameters.componentType}"
                };

                BridgeLogger.LogInfo($"Successfully added {parameters.componentType}");
                return BridgeResponse.Success(command.commandId, command.commandType, JsonUtility.ToJson(successResult));
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

        /// <summary>
        /// Find component type by name (supports short names and full names).
        /// </summary>
        private Type FindComponentType(string typeName)
        {
            // Try exact match first
            var type = Type.GetType(typeName);
            if (type != null)
                return type;

            // Search all assemblies for matching type
            foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
            {
                type = assembly.GetTypes().FirstOrDefault(t =>
                    (t.Name == typeName || t.FullName == typeName) &&
                    typeof(Component).IsAssignableFrom(t)
                );
                if (type != null)
                    return type;
            }

            return null;
        }

        /// <summary>
        /// Check if component type allows multiple instances.
        /// </summary>
        private bool AllowsDuplicates(Type componentType)
        {
            // Most Unity components don't allow duplicates
            // Some exceptions exist (like MonoBehaviours without DisallowMultipleComponent)
            var attribute = componentType.GetCustomAttributes(typeof(DisallowMultipleComponent), true);
            return attribute.Length == 0;
        }
    }
}

using System;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for GameObject operations (create, delete, rename).
    ///
    /// PURPOSE:
    /// Provides programmatic control over GameObject creation and manipulation in Unity Editor.
    /// Enables automated scene setup, GameObject hierarchy management, and test object creation
    /// from external tools like Claude Code.
    ///
    /// USE CASES:
    /// - Create GameObjects dynamically for scene setup
    /// - Delete GameObjects programmatically
    /// - Rename GameObjects for organization
    /// - Set parent-child relationships
    /// - Automated test scene configuration
    ///
    /// COMMAND JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "gameobject-operation",
    ///   "timestamp": "2025-10-06T12:00:00Z",
    ///   "parametersJson": "{\"operation\":\"create\",\"gameObjectName\":\"CameraManager\",\"parentPath\":\"\"}"
    /// }
    ///
    /// USAGE EXAMPLES:
    ///
    /// 1. Create empty GameObject:
    ///    send-command.ps1 -CommandType "gameobject-operation" -Parameters @{operation="create"; gameObjectName="CameraManager"}
    ///
    /// 2. Create GameObject with parent:
    ///    send-command.ps1 -CommandType "gameobject-operation" -Parameters @{operation="create"; gameObjectName="CM_FreeLook"; parentPath="CameraManager"}
    ///
    /// 3. Delete GameObject:
    ///    send-command.ps1 -CommandType "gameobject-operation" -Parameters @{operation="delete"; gameObjectPath="CameraManager/OldCamera"}
    ///
    /// 4. Rename GameObject:
    ///    send-command.ps1 -CommandType "gameobject-operation" -Parameters @{operation="rename"; gameObjectPath="Camera"; newName="MainCamera"}
    /// </summary>
    public class GameObjectOperationCommandHandler : ICommandHandler
    {
        public string CommandType => "gameobject-operation";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<GameObjectOperationParams>(command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new GameObjectOperationParams();

                BridgeLogger.LogDebug($"Executing operation: {parameters.operation}");

                GameObjectOperationResult result = null;

                switch (parameters.operation?.ToLower())
                {
                    case "create":
                        result = CreateGameObject(parameters);
                        break;

                    case "delete":
                        result = DeleteGameObject(parameters);
                        break;

                    case "rename":
                        result = RenameGameObject(parameters);
                        break;

                    default:
                        return BridgeResponse.Error(
                            command.commandId,
                            command.commandType,
                            $"Unknown operation: {parameters.operation}. Supported operations: create, delete, rename"
                        );
                }

                if (result.success)
                {
                    var resultJson = JsonUtility.ToJson(result);
                    return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
                }
                else
                {
                    return BridgeResponse.Error(command.commandId, command.commandType, result.message);
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        /// <summary>
        /// Create a new GameObject in the active scene.
        /// </summary>
        private GameObjectOperationResult CreateGameObject(GameObjectOperationParams parameters)
        {
            var result = new GameObjectOperationResult
            {
                operation = "create"
            };

            // Validate GameObject name
            if (string.IsNullOrEmpty(parameters.gameObjectName))
            {
                result.success = false;
                result.message = "GameObject name is required for create operation";
                return result;
            }

            try
            {
                // Create new GameObject
                var newGameObject = new GameObject(parameters.gameObjectName);

                // Set parent if specified
                if (!string.IsNullOrEmpty(parameters.parentPath))
                {
                    var parent = FindGameObjectByPath(parameters.parentPath);
                    if (parent == null)
                    {
                        result.success = false;
                        result.message = $"Parent GameObject not found: {parameters.parentPath}";
                        UnityEngine.Object.DestroyImmediate(newGameObject);
                        return result;
                    }

                    newGameObject.transform.SetParent(parent.transform, false);
                    result.gameObjectPath = $"{parameters.parentPath}/{parameters.gameObjectName}";
                }
                else
                {
                    result.gameObjectPath = parameters.gameObjectName;
                }

                // Mark scene dirty
                EditorUtility.SetDirty(newGameObject);
                UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());

                result.success = true;
                result.message = $"Successfully created GameObject: {parameters.gameObjectName}";
                BridgeLogger.LogInfo($"Created GameObject: {result.gameObjectPath}");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to create GameObject: {ex.Message}";
            }

            return result;
        }

        /// <summary>
        /// Delete a GameObject from the scene.
        /// </summary>
        private GameObjectOperationResult DeleteGameObject(GameObjectOperationParams parameters)
        {
            var result = new GameObjectOperationResult
            {
                operation = "delete"
            };

            // Validate GameObject path
            if (string.IsNullOrEmpty(parameters.gameObjectPath))
            {
                result.success = false;
                result.message = "GameObject path is required for delete operation";
                return result;
            }

            try
            {
                var gameObject = FindGameObjectByPath(parameters.gameObjectPath);
                if (gameObject == null)
                {
                    result.success = false;
                    result.message = $"GameObject not found: {parameters.gameObjectPath}";
                    return result;
                }

                result.gameObjectPath = parameters.gameObjectPath;

                // Delete the GameObject
                UnityEngine.Object.DestroyImmediate(gameObject);

                // Mark scene dirty
                UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());

                result.success = true;
                result.message = $"Successfully deleted GameObject: {parameters.gameObjectPath}";
                BridgeLogger.LogInfo($"Deleted GameObject: {parameters.gameObjectPath}");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to delete GameObject: {ex.Message}";
            }

            return result;
        }

        /// <summary>
        /// Rename a GameObject.
        /// </summary>
        private GameObjectOperationResult RenameGameObject(GameObjectOperationParams parameters)
        {
            var result = new GameObjectOperationResult
            {
                operation = "rename"
            };

            // Validate parameters
            if (string.IsNullOrEmpty(parameters.gameObjectPath))
            {
                result.success = false;
                result.message = "GameObject path is required for rename operation";
                return result;
            }

            if (string.IsNullOrEmpty(parameters.newName))
            {
                result.success = false;
                result.message = "New name is required for rename operation";
                return result;
            }

            try
            {
                var gameObject = FindGameObjectByPath(parameters.gameObjectPath);
                if (gameObject == null)
                {
                    result.success = false;
                    result.message = $"GameObject not found: {parameters.gameObjectPath}";
                    return result;
                }

                string oldPath = parameters.gameObjectPath;
                gameObject.name = parameters.newName;

                // Calculate new path
                var parent = gameObject.transform.parent;
                if (parent != null)
                {
                    result.gameObjectPath = $"{GetGameObjectPath(parent.gameObject)}/{parameters.newName}";
                }
                else
                {
                    result.gameObjectPath = parameters.newName;
                }

                // Mark scene dirty
                EditorUtility.SetDirty(gameObject);
                UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(gameObject.scene);

                result.success = true;
                result.message = $"Successfully renamed GameObject from '{oldPath}' to '{result.gameObjectPath}'";
                BridgeLogger.LogInfo($"Renamed GameObject: {oldPath} → {result.gameObjectPath}");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to rename GameObject: {ex.Message}";
            }

            return result;
        }

        /// <summary>
        /// Find GameObject by hierarchical path (e.g., "Parent/Child/GrandChild").
        /// </summary>
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
        /// Get full hierarchical path for a GameObject.
        /// </summary>
        private string GetGameObjectPath(GameObject go)
        {
            if (go.transform.parent == null)
                return go.name;

            return $"{GetGameObjectPath(go.transform.parent.gameObject)}/{go.name}";
        }
    }
}

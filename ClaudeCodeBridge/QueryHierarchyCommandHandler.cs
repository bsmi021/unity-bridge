using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for querying GameObject hierarchy in the active scene.
    ///
    /// PURPOSE:
    /// Inspects the Unity scene hierarchy to find GameObjects and their component structure.
    /// Useful for understanding scene organization, debugging object placement, and
    /// validating GameObject configurations.
    ///
    /// USE CASES:
    /// - Find all GameObjects with a specific name pattern
    /// - Get the complete component list for objects in a scene
    /// - Understand parent-child relationships in the hierarchy
    /// - Verify object activation states
    /// - Map out scene structure for debugging
    ///
    /// COMMAND JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "query-hierarchy",
    ///   "timestamp": "2025-10-05T18:00:00Z",
    ///   "parametersJson": "{\"gameObjectName\":\"Player\",\"includeInactive\":true,\"maxDepth\":3}"
    /// }
    ///
    /// USAGE EXAMPLES:
    ///
    /// 1. Find all Player-related objects:
    ///    send-command.ps1 -CommandType "query-hierarchy" -Parameters @{gameObjectName="Player"}
    ///
    /// 2. Get full scene hierarchy:
    ///    send-command.ps1 -CommandType "query-hierarchy" -Parameters @{includeInactive=$true}
    ///
    /// 3. Shallow hierarchy scan (root objects only):
    ///    send-command.ps1 -CommandType "query-hierarchy" -Parameters @{maxDepth=1}
    /// </summary>
    public class QueryHierarchyCommandHandler : ICommandHandler
    {
        public string CommandType => "query-hierarchy";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<QueryHierarchyParams>(command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new QueryHierarchyParams();

                BridgeLogger.LogDebug($"Querying hierarchy: name='{parameters.gameObjectName ?? "all"}', includeInactive={parameters.includeInactive}, maxDepth={parameters.maxDepth}");

                var result = new QueryHierarchyResult();
                var activeScene = SceneManager.GetActiveScene();
                var rootObjects = activeScene.GetRootGameObjects();

                foreach (var rootObject in rootObjects)
                {
                    if (!parameters.includeInactive && !rootObject.activeInHierarchy)
                        continue;

                    var objectInfo = BuildGameObjectInfo(rootObject, "", 0, parameters);
                    if (objectInfo != null)
                    {
                        result.gameObjects.Add(objectInfo);
                    }
                }

                result.totalCount = CountGameObjects(result.gameObjects);

                var resultJson = JsonUtility.ToJson(result);
                BridgeLogger.LogInfo($"Found {result.totalCount} GameObjects");

                return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        /// <summary>
        /// Recursively build GameObject information tree.
        /// </summary>
        private GameObjectInfo BuildGameObjectInfo(GameObject go, string parentPath, int depth, QueryHierarchyParams parameters)
        {
            // Check name filter
            if (!string.IsNullOrEmpty(parameters.gameObjectName))
            {
                if (!go.name.Contains(parameters.gameObjectName))
                {
                    // Check children before discarding
                    bool hasMatchingChildren = false;
                    if (parameters.maxDepth < 0 || depth < parameters.maxDepth)
                    {
                        for (int i = 0; i < go.transform.childCount; i++)
                        {
                            var child = go.transform.GetChild(i).gameObject;
                            if (!parameters.includeInactive && !child.activeInHierarchy)
                                continue;

                            var childInfo = BuildGameObjectInfo(child, go.name, depth + 1, parameters);
                            if (childInfo != null)
                            {
                                hasMatchingChildren = true;
                                break;
                            }
                        }
                    }

                    if (!hasMatchingChildren)
                        return null;
                }
            }

            // Build object info
            var info = new GameObjectInfo
            {
                name = go.name,
                path = string.IsNullOrEmpty(parentPath) ? go.name : $"{parentPath}/{go.name}",
                isActive = go.activeInHierarchy,
                tag = go.tag,
                layer = go.layer
            };

            // Get components
            var components = go.GetComponents<Component>();
            foreach (var component in components)
            {
                if (component != null)
                {
                    info.components.Add(component.GetType().FullName);
                }
            }

            // Process children
            if (parameters.maxDepth < 0 || depth < parameters.maxDepth)
            {
                for (int i = 0; i < go.transform.childCount; i++)
                {
                    var child = go.transform.GetChild(i).gameObject;
                    if (!parameters.includeInactive && !child.activeInHierarchy)
                        continue;

                    var childInfo = BuildGameObjectInfo(child, info.path, depth + 1, parameters);
                    if (childInfo != null)
                    {
                        info.children.Add(childInfo);
                    }
                }
            }

            return info;
        }

        /// <summary>
        /// Count total GameObjects in hierarchy tree.
        /// </summary>
        private int CountGameObjects(List<GameObjectInfo> objects)
        {
            int count = objects.Count;
            foreach (var obj in objects)
            {
                count += CountGameObjects(obj.children);
            }
            return count;
        }
    }
}

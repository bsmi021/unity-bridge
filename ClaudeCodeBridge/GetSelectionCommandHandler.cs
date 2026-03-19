using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for retrieving currently selected GameObjects in Unity Editor.
    ///
    /// PURPOSE:
    /// Gets information about GameObjects currently selected in the hierarchy view.
    /// Optionally includes component lists and child hierarchies.
    /// This enables querying the current editor state for automation workflows.
    ///
    /// USE CASES:
    /// - Check which object is currently selected
    /// - Get component list of selected objects
    /// - Inspect child structure of selected objects
    /// - Validate selection state after editor operations
    /// - Build workflows around selected objects
    ///
    /// COMMAND JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "get-selection",
    ///   "timestamp": "2025-01-06T18:00:00Z",
    ///   "parametersJson": "{\"includeComponents\":true,\"includeChildren\":false}"
    /// }
    ///
    /// RESPONSE JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "get-selection",
    ///   "status": "success",
    ///   "timestamp": "2025-01-06T18:00:01Z",
    ///   "dataJson": "{
    ///     \"count\": 1,
    ///     \"objects\": [
    ///       {
    ///         \"name\": \"Player\",
    ///         \"path\": \"Player\",
    ///         \"instanceId\": 12345,
    ///         \"components\": [\"Transform\", \"Rigidbody\", \"CharacterController\"],
    ///         \"children\": []
    ///       }
    ///     ]
    ///   }"
    /// }
    ///
    /// TECHNICAL DETAILS:
    /// Uses Selection.gameObjects to get currently selected objects.
    /// Recursively builds hierarchy information if includeChildren is true.
    /// Component names are retrieved as fully qualified type names.
    ///
    /// USAGE EXAMPLES:
    ///
    /// 1. Get selected object names:
    ///    & ".claude\unity\send-command.ps1" -CommandType "get-selection" -Parameters @{includeComponents=$false}
    ///
    /// 2. Get selected objects with components:
    ///    & ".claude\unity\send-command.ps1" -CommandType "get-selection" -Parameters @{includeComponents=$true}
    ///
    /// 3. Get full hierarchy of selected object:
    ///    & ".claude\unity\send-command.ps1" -CommandType "get-selection" `
    ///      -Parameters @{includeComponents=$true; includeChildren=$true}
    /// </summary>
    public class GetSelectionCommandHandler : ICommandHandler
    {
        public string CommandType => "get-selection";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                // Parse parameters from JSON
                var parameters = JsonUtility.FromJson<GetSelectionParams>(command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new GetSelectionParams();

                BridgeLogger.LogDebug($"Getting selection - includeComponents={parameters.includeComponents}, includeChildren={parameters.includeChildren}");

                // Get currently selected GameObjects
                var selectedObjects = Selection.gameObjects;

                // Build result
                var selectedInfoList = new List<SelectionInfo>();

                foreach (var go in selectedObjects)
                {
                    var info = BuildSelectionInfo(go, parameters);
                    selectedInfoList.Add(info);
                }

                // Build response
                var result = new GetSelectionResult
                {
                    count = selectedInfoList.Count,
                    objects = selectedInfoList
                };

                var resultJson = JsonUtility.ToJson(result, prettyPrint: true);

                BridgeLogger.LogInfo($"Retrieved {selectedInfoList.Count} selected objects");

                return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error getting selection: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        /// <summary>
        /// Builds selection information for a GameObject and optionally its children.
        /// </summary>
        private SelectionInfo BuildSelectionInfo(GameObject go, GetSelectionParams parameters)
        {
            var info = new SelectionInfo
            {
                name = go.name,
                path = GetGameObjectPath(go),
                instanceId = go.GetInstanceID(),
                components = new List<string>(),
                children = new List<SelectionInfo>()
            };

            // Add component names if requested
            if (parameters.includeComponents)
            {
                var components = go.GetComponents<Component>();
                foreach (var component in components)
                {
                    // Use the component's type name
                    info.components.Add(component.GetType().Name);
                }
            }

            // Add child objects if requested
            if (parameters.includeChildren)
            {
                var transform = go.transform;
                for (int i = 0; i < transform.childCount; i++)
                {
                    var child = transform.GetChild(i).gameObject;
                    var childInfo = BuildSelectionInfo(child, parameters);
                    info.children.Add(childInfo);
                }
            }

            return info;
        }

        /// <summary>
        /// Gets the full hierarchy path for a GameObject.
        /// Example: "Parent/Child/Grandchild"
        /// </summary>
        private string GetGameObjectPath(GameObject go)
        {
            var path = go.name;
            var parent = go.transform.parent;

            while (parent != null)
            {
                path = parent.name + "/" + path;
                parent = parent.parent;
            }

            return path;
        }

        /// <summary>
        /// Parameters for get-selection command.
        /// </summary>
        [System.Serializable]
        private class GetSelectionParams
        {
            public bool includeComponents = false;
            public bool includeChildren = false;
        }

        /// <summary>
        /// Information about a selected GameObject.
        /// </summary>
        [System.Serializable]
        private class SelectionInfo
        {
            public string name;
            public string path;
            public int instanceId;
            public List<string> components = new List<string>();
            public List<SelectionInfo> children = new List<SelectionInfo>();
        }

        /// <summary>
        /// Result data for get-selection command.
        /// </summary>
        [System.Serializable]
        private class GetSelectionResult
        {
            public int count;
            public List<SelectionInfo> objects = new List<SelectionInfo>();
        }
    }
}

using System;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for focusing the Unity scene view on a specific GameObject.
    ///
    /// PURPOSE:
    /// Focuses the active scene view camera on a specific GameObject, optionally
    /// framing it to fit in the view. This enables programmatic navigation of the scene.
    ///
    /// USE CASES:
    /// - Navigate to a specific object during inspection workflows
    /// - Frame objects for visual validation
    /// - Build automated scene exploration workflows
    /// - Focus on error locations during debugging
    /// - Validate GameObject placement in scene
    ///
    /// COMMAND JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "focus-object",
    ///   "timestamp": "2025-01-06T18:00:00Z",
    ///   "parametersJson": "{\"gameObjectPath\":\"Player/Camera\",\"frameSelection\":true}"
    /// }
    ///
    /// RESPONSE JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "focus-object",
    ///   "status": "success",
    ///   "timestamp": "2025-01-06T18:00:01Z",
    ///   "dataJson": "{
    ///     \"focused\": true,
    ///     \"gameObjectPath\": \"Player/Camera\",
    ///     \"message\": \"Focused on Player/Camera\"
    ///   }"
    /// }
    ///
    /// TECHNICAL DETAILS:
    /// 1. Uses GameObject.Find() to locate the object by path
    /// 2. Sets Selection.activeGameObject to select the target
    /// 3. Calls SceneView.lastActiveSceneView.FrameSelected() to frame the selection
    ///
    /// USAGE EXAMPLES:
    ///
    /// 1. Focus on root-level object:
    ///    & ".claude\unity\send-command.ps1" -CommandType "focus-object" `
    ///      -Parameters @{gameObjectPath="Player"; frameSelection=$true}
    ///
    /// 2. Focus on nested object without framing:
    ///    & ".claude\unity\send-command.ps1" -CommandType "focus-object" `
    ///      -Parameters @{gameObjectPath="Player/Head/Eyes"; frameSelection=$false}
    ///
    /// 3. Just select without changing camera:
    ///    & ".claude\unity\send-command.ps1" -CommandType "focus-object" `
    ///      -Parameters @{gameObjectPath="UI/Canvas"; frameSelection=$false}
    /// </summary>
    public class FocusObjectCommandHandler : ICommandHandler
    {
        public string CommandType => "focus-object";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                // Parse parameters from JSON
                var parameters = JsonUtility.FromJson<FocusObjectParams>(command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new FocusObjectParams();

                // Validate required parameter
                if (string.IsNullOrEmpty(parameters.gameObjectPath))
                {
                    return BridgeResponse.Error(
                        command.commandId,
                        command.commandType,
                        "gameObjectPath parameter is required"
                    );
                }

                BridgeLogger.LogDebug($"Focusing on object: {parameters.gameObjectPath}, frameSelection={parameters.frameSelection}");

                // Find the GameObject by path
                var targetObject = GameObject.Find(parameters.gameObjectPath);

                if (targetObject == null)
                {
                    return BridgeResponse.Error(
                        command.commandId,
                        command.commandType,
                        $"GameObject not found: {parameters.gameObjectPath}"
                    );
                }

                // Select the object
                Selection.activeGameObject = targetObject;

                // Frame the selection in scene view if requested
                if (parameters.frameSelection)
                {
                    var sceneView = SceneView.lastActiveSceneView;
                    if (sceneView != null)
                    {
                        sceneView.FrameSelected();
                    }
                    else
                    {
                        BridgeLogger.LogWarning("No active scene view found - cannot frame selection");
                    }
                }

                BridgeLogger.LogInfo($"Successfully focused on {parameters.gameObjectPath}");

                // Build response
                var result = new FocusObjectResult
                {
                    focused = true,
                    gameObjectPath = parameters.gameObjectPath,
                    message = $"Focused on {parameters.gameObjectPath}"
                };

                var resultJson = JsonUtility.ToJson(result);
                return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error focusing on object: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        /// <summary>
        /// Parameters for focus-object command.
        /// </summary>
        [System.Serializable]
        private class FocusObjectParams
        {
            public string gameObjectPath;
            public bool frameSelection = true;
        }

        /// <summary>
        /// Result data for focus-object command.
        /// </summary>
        [System.Serializable]
        private class FocusObjectResult
        {
            public bool focused;
            public string gameObjectPath;
            public string message;
        }
    }
}

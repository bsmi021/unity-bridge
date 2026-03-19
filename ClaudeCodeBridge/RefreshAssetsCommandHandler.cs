using System;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for triggering AssetDatabase refresh in Unity.
    ///
    /// PURPOSE:
    /// Triggers a refresh of the Unity AssetDatabase, optionally forcing reimport
    /// of all assets. This is useful after external file changes or during workflows
    /// that need to synchronize asset state.
    ///
    /// USE CASES:
    /// - Force asset reimport after external file modifications
    /// - Synchronize asset state during automated workflows
    /// - Detect newly created asset files
    /// - Trigger shader recompilation
    /// - Refresh asset metadata after batch operations
    ///
    /// COMMAND JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "refresh-assets",
    ///   "timestamp": "2025-01-06T18:00:00Z",
    ///   "parametersJson": "{\"forceUpdate\":false}"
    /// }
    ///
    /// RESPONSE JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "refresh-assets",
    ///   "status": "success",
    ///   "timestamp": "2025-01-06T18:00:01Z",
    ///   "dataJson": "{
    ///     \"refreshed\": true,
    ///     \"forceUpdate\": false,
    ///     \"message\": \"Asset database refreshed successfully\"
    ///   }"
    /// }
    ///
    /// TECHNICAL DETAILS:
    /// Calls AssetDatabase.Refresh() with optional ImportAssetOptions.ForceUpdate flag.
    /// - Default mode: Quick refresh, only reimports files that have changed
    /// - forceUpdate=true: Forces complete reimport of all assets (slower but thorough)
    ///
    /// USAGE EXAMPLES:
    ///
    /// 1. Quick asset refresh (detect new files):
    ///    & ".claude\unity\send-command.ps1" -CommandType "refresh-assets" -Parameters @{forceUpdate=$false}
    ///
    /// 2. Force complete reimport of all assets:
    ///    & ".claude\unity\send-command.ps1" -CommandType "refresh-assets" -Parameters @{forceUpdate=$true}
    /// </summary>
    public class RefreshAssetsCommandHandler : ICommandHandler
    {
        public string CommandType => "refresh-assets";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                // Parse parameters from JSON
                var parameters = JsonUtility.FromJson<RefreshAssetsParams>(command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new RefreshAssetsParams();

                BridgeLogger.LogDebug($"Refreshing assets - forceUpdate={parameters.forceUpdate}");

                // Determine import options based on parameters
                var options = parameters.forceUpdate
                    ? ImportAssetOptions.ForceUpdate
                    : ImportAssetOptions.Default;

                // Trigger asset database refresh
                AssetDatabase.Refresh(options);

                BridgeLogger.LogInfo("Asset database refreshed successfully");

                // Build response
                var result = new RefreshAssetsResult
                {
                    refreshed = true,
                    forceUpdate = parameters.forceUpdate,
                    message = "Asset database refreshed successfully"
                };

                var resultJson = JsonUtility.ToJson(result);
                return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error refreshing assets: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        /// <summary>
        /// Parameters for refresh-assets command.
        /// </summary>
        [System.Serializable]
        private class RefreshAssetsParams
        {
            public bool forceUpdate = false;
        }

        /// <summary>
        /// Result data for refresh-assets command.
        /// </summary>
        [System.Serializable]
        private class RefreshAssetsResult
        {
            public bool refreshed;
            public bool forceUpdate;
            public string message;
        }
    }
}

using System;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for occlusion culling operations.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "bake"         - Compute occlusion culling data
    /// 2. "clear"        - Clear occlusion culling data
    /// 3. "get-settings" - Get current occlusion culling settings
    /// </summary>
    public class OcclusionCullingCommandHandler : ICommandHandler
    {
        public string CommandType => "occlusion-culling";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Cannot perform occlusion culling operations while scripts are compiling.");
                }

                var parameters = JsonUtility.FromJson<OcclusionCullingParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new OcclusionCullingParams();

                BridgeLogger.LogDebug($"Executing occlusion-culling operation: {parameters.operation}");

                switch (parameters.operation?.ToLower())
                {
                    case "bake":
                        return ExecuteBake(command);
                    case "clear":
                        return ExecuteClear(command);
                    case "get-settings":
                        return ExecuteGetSettings(command);
                    default:
                        return BridgeResponse.Error(
                            command.commandId, command.commandType,
                            $"Unknown occlusion-culling operation: {parameters.operation}. "
                            + "Supported: bake, clear, get-settings");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"OcclusionCulling operation error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse ExecuteBake(BridgeCommand command)
        {
            if (EditorApplication.isPlaying)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "Cannot bake occlusion culling while in Play mode.");
            }

            StaticOcclusionCulling.Compute();

            var result = new OcclusionCullingResult
            {
                operation = "bake",
                success = true,
                message = "Occlusion culling computation started"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteClear(BridgeCommand command)
        {
            if (EditorApplication.isPlaying)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "Cannot clear occlusion culling while in Play mode.");
            }

            StaticOcclusionCulling.Clear();

            var result = new OcclusionCullingResult
            {
                operation = "clear",
                success = true,
                message = "Occlusion culling data cleared"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteGetSettings(BridgeCommand command)
        {
            var result = new OcclusionCullingSettingsResult
            {
                operation = "get-settings",
                smallestOccluder = StaticOcclusionCulling.smallestOccluder,
                smallestHole = StaticOcclusionCulling.smallestHole,
                backfaceThreshold = StaticOcclusionCulling.backfaceThreshold,
                isComputing = StaticOcclusionCulling.isRunning,
                doesSceneHaveManualPortals = StaticOcclusionCulling.doesSceneHaveManualPortals,
                success = true,
                message = "Occlusion culling settings retrieved"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }
    }

    // -----------------------------------------------------------------
    // Models
    // -----------------------------------------------------------------

    [Serializable]
    public class OcclusionCullingParams
    {
        public string operation;
    }

    [Serializable]
    public class OcclusionCullingResult
    {
        public string operation;
        public bool success;
        public string message;
    }

    [Serializable]
    public class OcclusionCullingSettingsResult
    {
        public string operation;
        public float smallestOccluder;
        public float smallestHole;
        public float backfaceThreshold;
        public bool isComputing;
        public bool doesSceneHaveManualPortals;
        public bool success;
        public string message;
    }
}

using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for Time settings operations.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "get" - Read current time settings
    /// 2. "set" - Modify time settings
    ///
    /// GUARDS:
    /// - EditorApplication.isCompiling: blocks all operations
    /// - EditorApplication.isPlaying: blocks set operation
    /// </summary>
    public class TimeSettingsCommandHandler : ICommandHandler
    {
        public string CommandType => "time-settings";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Cannot access time settings while scripts are compiling.");
                }

                var parameters = JsonUtility.FromJson<TimeSettingsParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new TimeSettingsParams();

                TimeSettingsResult result;
                switch (parameters.operation?.ToLower())
                {
                    case "get":
                        result = ExecuteGet();
                        break;
                    case "set":
                        result = ExecuteSet(parameters);
                        break;
                    default:
                        result = new TimeSettingsResult
                        {
                            success = false,
                            operation = parameters.operation,
                            message = $"Unknown operation: {parameters.operation}. "
                                + "Supported: get, set"
                        };
                        break;
                }

                var resultJson = JsonUtility.ToJson(result);
                return BridgeResponse.Success(
                    command.commandId, command.commandType, resultJson);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"TimeSettings error: {ex}");
                return BridgeResponse.Error(
                    command.commandId, command.commandType, ex.ToString());
            }
        }

        private TimeSettingsResult ExecuteGet()
        {
            return new TimeSettingsResult
            {
                success = true,
                operation = "get",
                fixedDeltaTime = Time.fixedDeltaTime,
                maximumDeltaTime = Time.maximumDeltaTime,
                timeScale = Time.timeScale,
                maximumParticleDeltaTime = Time.maximumParticleDeltaTime,
                captureDeltaTime = Time.captureDeltaTime,
                message = "Time settings retrieved"
            };
        }

        private TimeSettingsResult ExecuteSet(TimeSettingsParams p)
        {
            if (EditorApplication.isPlaying)
            {
                return new TimeSettingsResult
                {
                    success = false,
                    operation = "set",
                    message = "Cannot modify time settings in play mode."
                };
            }

            if (p.setFixedDeltaTime)
                Time.fixedDeltaTime = p.fixedDeltaTime;
            if (p.setMaximumDeltaTime)
                Time.maximumDeltaTime = p.maximumDeltaTime;
            if (p.setTimeScale)
                Time.timeScale = p.timeScale;
            if (p.setMaximumParticleDeltaTime)
                Time.maximumParticleDeltaTime = p.maximumParticleDeltaTime;
            if (p.setCaptureDeltaTime)
                Time.captureDeltaTime = p.captureDeltaTime;

            EditorUtility.SetDirty(
                AssetDatabase.LoadMainAssetAtPath(
                    "ProjectSettings/TimeManager.asset"));

            var result = ExecuteGet();
            result.operation = "set";
            result.message = "Time settings updated";
            return result;
        }
    }

    // -----------------------------------------------------------------
    // Models
    // -----------------------------------------------------------------

    [Serializable]
    public class TimeSettingsParams
    {
        public string operation;

        public float fixedDeltaTime;
        public bool setFixedDeltaTime;
        public float maximumDeltaTime;
        public bool setMaximumDeltaTime;
        public float timeScale;
        public bool setTimeScale;
        public float maximumParticleDeltaTime;
        public bool setMaximumParticleDeltaTime;
        public float captureDeltaTime;
        public bool setCaptureDeltaTime;
    }

    [Serializable]
    public class TimeSettingsResult
    {
        public bool success;
        public string operation;
        public string message;
        public float fixedDeltaTime;
        public float maximumDeltaTime;
        public float timeScale;
        public float maximumParticleDeltaTime;
        public float captureDeltaTime;
    }
}

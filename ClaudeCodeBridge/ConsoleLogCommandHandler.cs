using System;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for logging custom messages to the Unity Console.
    ///
    /// PURPOSE:
    /// Allows external tools to write log, warning, or error messages
    /// directly to the Unity Console for debugging and feedback.
    ///
    /// COMMAND JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "console-log",
    ///   "parametersJson": "{\"message\":\"Build started\",\"logType\":\"log\"}"
    /// }
    /// </summary>
    public class ConsoleLogCommandHandler : ICommandHandler
    {
        public string CommandType => "console-log";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<ConsoleLogParams>(
                    command.parametersJson ?? "{}");

                if (parameters == null || string.IsNullOrEmpty(parameters.message))
                {
                    return BridgeResponse.Error(
                        command.commandId, command.commandType,
                        "Missing required parameter: message");
                }

                switch (parameters.logType?.ToLower())
                {
                    case "warning":
                        Debug.LogWarning($"[Bridge] {parameters.message}");
                        break;
                    case "error":
                        Debug.LogError($"[Bridge] {parameters.message}");
                        break;
                    default:
                        Debug.Log($"[Bridge] {parameters.message}");
                        break;
                }

                var result = new ConsoleLogResult
                {
                    success = true,
                    logType = parameters.logType ?? "log",
                    message = parameters.message,
                };

                return BridgeResponse.Success(
                    command.commandId, command.commandType, JsonUtility.ToJson(result));
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }
    }

    [Serializable]
    public class ConsoleLogParams
    {
        public string message;
        public string logType; // "log", "warning", "error"
    }

    [Serializable]
    public class ConsoleLogResult
    {
        public bool success;
        public string logType;
        public string message;
    }
}

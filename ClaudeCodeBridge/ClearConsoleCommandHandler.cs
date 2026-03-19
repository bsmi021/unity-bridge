using System;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for clearing Unity console logs.
    ///
    /// PURPOSE:
    /// Clears all log entries from the Unity Editor Console window.
    /// This enables clean test output and diagnostic workflows.
    ///
    /// USE CASES:
    /// - Clear console before running tests for clean output
    /// - Reset console state between diagnostic checks
    /// - Get fresh console logs for specific operations
    /// - Reduce console spam during long-running operations
    ///
    /// COMMAND JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "clear-console",
    ///   "timestamp": "2025-01-06T18:00:00Z",
    ///   "parametersJson": "{}"
    /// }
    ///
    /// RESPONSE JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "clear-console",
    ///   "status": "success",
    ///   "timestamp": "2025-01-06T18:00:01Z",
    ///   "dataJson": "{
    ///     \"cleared\": true,
    ///     \"message\": \"Console cleared successfully\"
    ///   }"
    /// }
    ///
    /// TECHNICAL DETAILS:
    /// Uses reflection to access Unity's internal LogEntries.Clear() method.
    /// The LogEntries class is not publicly exposed but can be accessed via reflection
    /// on UnityEditor assembly. This is a stable internal API used by the console UI.
    ///
    /// USAGE EXAMPLES:
    ///
    /// 1. Clear console before running tests:
    ///    & ".claude\unity\send-command.ps1" -CommandType "clear-console"
    ///
    /// 2. Clear and read to verify clean state:
    ///    & ".claude\unity\send-command.ps1" -CommandType "clear-console"
    ///    & ".claude\unity\send-command.ps1" -CommandType "read-console"
    /// </summary>
    public class ClearConsoleCommandHandler : ICommandHandler
    {
        public string CommandType => "clear-console";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                BridgeLogger.LogDebug("Clearing console logs...");

                // Access Unity's internal LogEntries class via reflection
                // The LogEntries class is in UnityEditor assembly and not public,
                // but it provides the Clear() method used by the editor console UI
                var logEntriesType = Type.GetType("UnityEditor.LogEntries,UnityEditor");

                if (logEntriesType == null)
                {
                    return BridgeResponse.Error(
                        command.commandId,
                        command.commandType,
                        "Failed to find UnityEditor.LogEntries type. Console clearing not available."
                    );
                }

                // Get the static Clear method
                var clearMethod = logEntriesType.GetMethod(
                    "Clear",
                    BindingFlags.Static | BindingFlags.Public
                );

                if (clearMethod == null)
                {
                    return BridgeResponse.Error(
                        command.commandId,
                        command.commandType,
                        "Failed to find LogEntries.Clear() method. Console clearing not available."
                    );
                }

                // Invoke Clear() to clear all console logs
                try
                {
                    clearMethod.Invoke(null, null);
                }
                catch (TargetInvocationException ex)
                {
                    // Unwrap the actual exception
                    throw ex.InnerException ?? ex;
                }

                BridgeLogger.LogInfo("Console cleared successfully");

                // Build success result
                var result = new ClearConsoleResult
                {
                    cleared = true,
                    message = "Console cleared successfully"
                };

                var resultJson = JsonUtility.ToJson(result);
                return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error clearing console: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        /// <summary>
        /// Result data for clear-console command.
        /// </summary>
        [System.Serializable]
        private class ClearConsoleResult
        {
            public bool cleared;
            public string message;
        }
    }
}

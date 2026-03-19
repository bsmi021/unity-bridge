using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for retrieving Claude Unity Bridge status and health information.
    ///
    /// PURPOSE:
    /// Provides diagnostic information about the bridge system's configuration and state.
    /// This enables Claude Code to verify connectivity, check registered handlers, and
    /// understand the current Unity environment before sending commands.
    ///
    /// USE CASES:
    /// - Verify bridge is operational before running command sequences
    /// - Check which command handlers are available
    /// - Understand current Unity state (scene, play mode)
    /// - Debug bridge connectivity issues
    /// - Validate paths for command/response file operations
    /// - Monitor bridge usage metrics (commands processed)
    ///
    /// COMMAND JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "bridge-status",
    ///   "timestamp": "2025-10-07T18:00:00Z",
    ///   "parametersJson": "{}"
    /// }
    ///
    /// RESPONSE JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "bridge-status",
    ///   "status": "success",
    ///   "timestamp": "2025-10-07T18:00:01Z",
    ///   "dataJson": "{
    ///     \"unityVersion\": \"6000.2.0f1\",
    ///     \"isInitialized\": true,
    ///     \"registeredHandlers\": [\"run-tests\", \"query-hierarchy\", \"bridge-status\", ...],
    ///     \"commandsProcessed\": 42,
    ///     \"commandsPath\": \"C:/Projects/rpg.game/.claude/unity/commands\",
    ///     \"responsesPath\": \"C:/Projects/rpg.game/.claude/unity/responses\",
    ///     \"currentScene\": \"Assets/Scenes/GameplayScene.unity\",
    ///     \"playModeState\": \"Stopped\"
    ///   }"
    /// }
    ///
    /// TECHNICAL DETAILS:
    /// Uses reflection to access ClaudeUnityBridge's private fields (_commandHandlers, _processedCommandFiles)
    /// to report accurate handler registration and usage metrics. This allows the status command to provide
    /// comprehensive diagnostics without exposing internal state through public APIs.
    ///
    /// USAGE EXAMPLES:
    ///
    /// 1. Quick health check before automation:
    ///    & ".claude\unity\send-command.ps1" -CommandType "bridge-status"
    ///
    /// 2. Verify specific handler is available:
    ///    $status = & ".claude\unity\send-command.ps1" -CommandType "bridge-status"
    ///    if ($status.registeredHandlers -contains "run-tests") { ... }
    ///
    /// 3. Check play mode before sending commands:
    ///    $status = & ".claude\unity\send-command.ps1" -CommandType "bridge-status"
    ///    if ($status.playModeState -eq "Playing") { ... }
    /// </summary>
    public class BridgeStatusCommandHandler : ICommandHandler
    {
        public string CommandType => "bridge-status";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                BridgeLogger.LogDebug("Collecting bridge status information...");

                // Create result object to populate with status information
                var result = new BridgeStatusResult();

                // Collect Unity version information
                // Application.unityVersion returns full version string (e.g., "6000.2.0f1")
                result.unityVersion = Application.unityVersion;

                // Bridge is initialized if this handler is executing
                // The fact that we're running means the bridge static constructor has executed
                result.isInitialized = true;

                // Get registered command handlers from ClaudeUnityBridge
                // We use reflection to access the private _commandHandlers dictionary
                // This provides an accurate list of all available command types
                result.registeredHandlers = GetRegisteredHandlers();

                // Get count of processed commands from ClaudeUnityBridge
                // This metric shows how many commands have been executed since Unity started
                result.commandsProcessed = GetCommandsProcessedCount();

                // Get file system paths for commands and responses
                // These paths are where Claude Code writes commands and reads responses
                var projectRoot = Directory.GetParent(Application.dataPath).FullName;
                result.commandsPath = Path.Combine(projectRoot, ".claude", "unity", "commands");
                result.responsesPath = Path.Combine(projectRoot, ".claude", "unity", "responses");

                // Get current active scene name
                // This helps Claude Code understand the current Unity context
                var activeScene = EditorSceneManager.GetActiveScene();
                result.currentScene = activeScene.path;

                // Get editor play mode state
                // Values: "Stopped", "Playing", "Paused"
                // This is critical for commands that require specific play mode states
                result.playModeState = GetPlayModeState();

                // Serialize result to JSON
                var resultJson = JsonUtility.ToJson(result, prettyPrint: true);

                BridgeLogger.LogInfo($"Status collected - Unity {result.unityVersion}, " +
                         $"{result.registeredHandlers.Count} handlers, {result.commandsProcessed} commands processed, " +
                         $"Scene: {result.currentScene}, PlayMode: {result.playModeState}");

                return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error collecting status: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        /// <summary>
        /// Gets the list of registered command handler names from ClaudeUnityBridge.
        /// Uses reflection to access the private _commandHandlers dictionary.
        /// </summary>
        /// <returns>List of command type names (e.g., "run-tests", "query-hierarchy")</returns>
        private List<string> GetRegisteredHandlers()
        {
            try
            {
                // Get ClaudeUnityBridge type from current assembly
                var bridgeType = typeof(ClaudeUnityBridge);

                // Get the private static _instance field
                var instanceField = bridgeType.GetField("_instance",
                    System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);

                if (instanceField == null)
                {
                    BridgeLogger.LogWarning("Could not find _instance field");
                    return new List<string> { "reflection-failed" };
                }

                // Get the instance value
                var instance = instanceField.GetValue(null);
                if (instance == null)
                {
                    BridgeLogger.LogWarning("Bridge instance is null");
                    return new List<string> { "instance-null" };
                }

                // Get the private _commandHandlers dictionary field
                var handlersField = bridgeType.GetField("_commandHandlers",
                    System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);

                if (handlersField == null)
                {
                    BridgeLogger.LogWarning("Could not find _commandHandlers field");
                    return new List<string> { "handlers-field-not-found" };
                }

                // Get the dictionary value
                var handlers = handlersField.GetValue(instance) as Dictionary<string, ICommandHandler>;
                if (handlers == null)
                {
                    BridgeLogger.LogWarning("Handlers dictionary is null");
                    return new List<string> { "handlers-null" };
                }

                // Return sorted list of handler names for consistent output
                return handlers.Keys.OrderBy(k => k).ToList();
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error getting registered handlers: {ex}");
                return new List<string> { "error: " + ex.Message };
            }
        }

        /// <summary>
        /// Gets the count of commands processed by the bridge since Unity started.
        /// Uses reflection to access the private _processedCommandFiles HashSet.
        /// </summary>
        /// <returns>Number of commands processed</returns>
        private int GetCommandsProcessedCount()
        {
            try
            {
                // Get ClaudeUnityBridge type from current assembly
                var bridgeType = typeof(ClaudeUnityBridge);

                // Get the private static _instance field
                var instanceField = bridgeType.GetField("_instance",
                    System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);

                if (instanceField == null)
                {
                    BridgeLogger.LogWarning("Could not find _instance field for commands count");
                    return -1;
                }

                // Get the instance value
                var instance = instanceField.GetValue(null);
                if (instance == null)
                {
                    BridgeLogger.LogWarning("Bridge instance is null for commands count");
                    return -1;
                }

                // Get the private _processedCommandFiles HashSet field
                var processedField = bridgeType.GetField("_processedCommandFiles",
                    System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);

                if (processedField == null)
                {
                    BridgeLogger.LogWarning("Could not find _processedCommandFiles field");
                    return -1;
                }

                // Get the HashSet value
                var processedFiles = processedField.GetValue(instance) as System.Collections.ICollection;
                if (processedFiles == null)
                {
                    BridgeLogger.LogWarning("_processedCommandFiles is null");
                    return -1;
                }

                // Return the count of processed command files
                return processedFiles.Count;
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error getting commands processed count: {ex}");
                return -1;
            }
        }

        /// <summary>
        /// Gets the current editor play mode state.
        /// </summary>
        /// <returns>"Stopped", "Playing", or "Paused"</returns>
        private string GetPlayModeState()
        {
            // EditorApplication.isPlaying indicates if Unity is in play mode
            // EditorApplication.isPaused indicates if play mode is paused
            if (!EditorApplication.isPlaying)
            {
                return "Stopped";
            }
            else if (EditorApplication.isPaused)
            {
                return "Paused";
            }
            else
            {
                return "Playing";
            }
        }
    }
}

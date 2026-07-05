using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for controlling Unity Editor play mode state.
    ///
    /// This handler allows Claude Code to programmatically control the Unity Editor's
    /// play mode, including entering/exiting play mode, pausing, stepping frames, and
    /// querying the current play mode state.
    ///
    /// Command JSON format:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "playmode-control",
    ///   "timestamp": "2025-10-06T00:00:00Z",
    ///   "parametersJson": "{\"operation\":\"play\",\"targetScene\":\"Assets/Scenes/TestScene.unity\"}"
    /// }
    ///
    /// Supported operations:
    /// - "play": Enter play mode (optionally load scene first)
    /// - "pause": Pause play mode
    /// - "stop": Exit play mode
    /// - "step": Step one frame (when paused)
    /// - "status": Get current play mode state
    /// </summary>
    public class PlayModeControlCommandHandler : ICommandHandler
    {
        public string CommandType => "playmode-control";

        // Track pending state changes and their command IDs
        private static Dictionary<string, PendingStateChange> _pendingStateChanges = new Dictionary<string, PendingStateChange>();

        /// <summary>
        /// Static constructor to register play mode state change callback.
        /// This callback is used to write final responses when async state changes complete.
        /// </summary>
        static PlayModeControlCommandHandler()
        {
            EditorApplication.playModeStateChanged += OnPlayModeStateChanged;
        }

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                // Parse parameters
                var parameters = JsonUtility.FromJson<PlayModeControlParams>(command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new PlayModeControlParams();

                // Validate operation
                string operation = ResolveOperation(parameters);
                if (string.IsNullOrEmpty(operation))
                {
                    return BridgeResponse.Error(command.commandId, command.commandType, "Operation parameter is required");
                }

                BridgeLogger.LogDebug($"Executing operation: {operation}");

                // Execute the requested operation
                switch (operation.ToLowerInvariant())
                {
                    case "play":
                        return HandlePlay(command, parameters);

                    case "pause":
                        return HandlePause(command, parameters);

                    case "stop":
                        return HandleStop(command, parameters);

                    case "step":
                        return HandleStep(command, parameters);

                    case "status":
                        return HandleStatus(command, parameters);

                    default:
                        return BridgeResponse.Error(
                            command.commandId,
                            command.commandType,
                            $"Unknown operation: {operation}. Supported operations: play, pause, stop, step, status"
                        );
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        #region Operation Handlers

        /// <summary>
        /// Handle the "play" operation - enter play mode.
        /// Optionally loads a target scene before entering play mode.
        /// </summary>
        private BridgeResponse HandlePlay(BridgeCommand command, PlayModeControlParams parameters)
        {
            // If already playing, return current state
            if (EditorApplication.isPlaying)
            {
                var result = CreateResult(parameters.operation, "Already in play mode");
                return BridgeResponse.Success(command.commandId, command.commandType, JsonUtility.ToJson(result));
            }

            // Load target scene if specified
            if (!string.IsNullOrEmpty(parameters.targetScene))
            {
                try
                {
                    // Validate scene path
                    if (!System.IO.File.Exists(parameters.targetScene))
                    {
                        return BridgeResponse.Error(
                            command.commandId,
                            command.commandType,
                            $"Scene not found: {parameters.targetScene}"
                        );
                    }

                    var ready = BridgeSceneModalRecovery.PrepareForAutomation("playmode-control play",
                        out var modalMessage);
                    if (!ready)
                    {
                        return BridgeResponse.Error(
                            command.commandId,
                            command.commandType,
                            modalMessage
                        );
                    }

                    BridgeLogger.LogDebug($"Loading scene: {parameters.targetScene}");
                    EditorSceneManager.OpenScene(parameters.targetScene, OpenSceneMode.Single);
                }
                catch (Exception ex)
                {
                    return BridgeResponse.Error(
                        command.commandId,
                        command.commandType,
                        $"Failed to load scene: {ex.Message}"
                    );
                }
            }

            // Register pending state change
            _pendingStateChanges[command.commandId] = new PendingStateChange
            {
                CommandId = command.commandId,
                Operation = parameters.operation,
                TargetState = PlayModeStateChange.EnteredPlayMode
            };

            // Enter play mode (this is async)
            EditorApplication.isPlaying = true;

            // Return "running" response - final response will be written in callback
            return BridgeResponse.Running(
                command.commandId,
                command.commandType,
                JsonUtility.ToJson(new PlayModeControlResult
                {
                    operation = parameters.operation,
                    playModeState = "Transitioning",
                    isPaused = false,
                    currentScene = SceneManager.GetActiveScene().path,
                    success = true,
                    message = "Entering play mode..."
                })
            );
        }

        /// <summary>
        /// Handle the "pause" operation - pause or unpause play mode.
        /// </summary>
        private BridgeResponse HandlePause(BridgeCommand command, PlayModeControlParams parameters)
        {
            if (!EditorApplication.isPlaying)
            {
                return BridgeResponse.Error(
                    command.commandId,
                    command.commandType,
                    "Cannot pause - not in play mode"
                );
            }

            // Toggle pause state
            EditorApplication.isPaused = !EditorApplication.isPaused;

            var result = CreateResult(
                parameters.operation,
                EditorApplication.isPaused ? "Play mode paused" : "Play mode unpaused"
            );

            return BridgeResponse.Success(command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        /// <summary>
        /// Handle the "stop" operation - exit play mode.
        /// </summary>
        private BridgeResponse HandleStop(BridgeCommand command, PlayModeControlParams parameters)
        {
            if (!EditorApplication.isPlaying)
            {
                var result = CreateResult(parameters.operation, "Already stopped");
                return BridgeResponse.Success(command.commandId, command.commandType, JsonUtility.ToJson(result));
            }

            // Register pending state change
            _pendingStateChanges[command.commandId] = new PendingStateChange
            {
                CommandId = command.commandId,
                Operation = parameters.operation,
                TargetState = PlayModeStateChange.EnteredEditMode
            };

            // Exit play mode (this is async)
            EditorApplication.isPlaying = false;

            // Return "running" response - final response will be written in callback
            return BridgeResponse.Running(
                command.commandId,
                command.commandType,
                JsonUtility.ToJson(new PlayModeControlResult
                {
                    operation = parameters.operation,
                    playModeState = "Transitioning",
                    isPaused = false,
                    currentScene = SceneManager.GetActiveScene().path,
                    success = true,
                    message = "Exiting play mode..."
                })
            );
        }

        /// <summary>
        /// Handle the "step" operation - step one frame while paused.
        /// </summary>
        private BridgeResponse HandleStep(BridgeCommand command, PlayModeControlParams parameters)
        {
            if (!EditorApplication.isPlaying)
            {
                return BridgeResponse.Error(
                    command.commandId,
                    command.commandType,
                    "Cannot step - not in play mode"
                );
            }

            if (!EditorApplication.isPaused)
            {
                return BridgeResponse.Error(
                    command.commandId,
                    command.commandType,
                    "Cannot step - play mode is not paused"
                );
            }

            // Step one frame
            EditorApplication.Step();

            var result = CreateResult(parameters.operation, "Stepped one frame");
            return BridgeResponse.Success(command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        /// <summary>
        /// Handle the "status" operation - get current play mode state.
        /// </summary>
        private BridgeResponse HandleStatus(BridgeCommand command, PlayModeControlParams parameters)
        {
            var result = CreateResult(parameters.operation, "Current play mode state");
            return BridgeResponse.Success(command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        #endregion

        #region State Change Callback

        /// <summary>
        /// Called when play mode state changes.
        /// Writes final responses for pending state changes.
        /// </summary>
        private static void OnPlayModeStateChanged(PlayModeStateChange state)
        {
            BridgeLogger.LogDebug($"Play mode state changed: {state}");

            // Find any pending state changes waiting for this state
            var completedChanges = new List<string>();

            foreach (var kvp in _pendingStateChanges)
            {
                var pending = kvp.Value;

                // Check if this state change matches what we're waiting for
                if (pending.TargetState == state)
                {
                    try
                    {
                        var result = CreateResult(
                            pending.Operation,
                            GetStateMessage(state)
                        );

                        ClaudeUnityBridge.WriteResponseStatic(
                            BridgeResponse.Success(pending.CommandId, "playmode-control", JsonUtility.ToJson(result))
                        );

                        completedChanges.Add(kvp.Key);
                    }
                    catch (Exception ex)
                    {
                        BridgeLogger.LogError($"Error writing final response: {ex}");
                        ClaudeUnityBridge.WriteResponseStatic(
                            BridgeResponse.Error(pending.CommandId, "playmode-control", ex.ToString())
                        );
                        completedChanges.Add(kvp.Key);
                    }
                }
            }

            // Clean up completed changes
            foreach (var commandId in completedChanges)
            {
                _pendingStateChanges.Remove(commandId);
            }
        }

        #endregion

        #region Helper Methods

        /// <summary>
        /// Resolve the canonical operation value, accepting the legacy action alias.
        /// </summary>
        private static string ResolveOperation(PlayModeControlParams parameters)
        {
            string operation = !string.IsNullOrWhiteSpace(parameters.operation)
                ? parameters.operation
                : parameters.action;
            operation = operation?.Trim();
            parameters.operation = operation;
            return operation;
        }

        /// <summary>
        /// Create a result object with current play mode state.
        /// </summary>
        private static PlayModeControlResult CreateResult(string operation, string message)
        {
            return new PlayModeControlResult
            {
                operation = operation,
                playModeState = GetPlayModeState(),
                isPaused = EditorApplication.isPaused,
                currentScene = SceneManager.GetActiveScene().path,
                success = true,
                message = message
            };
        }

        /// <summary>
        /// Get the current play mode state as a string.
        /// </summary>
        private static string GetPlayModeState()
        {
            if (!EditorApplication.isPlaying)
                return "Stopped";

            if (EditorApplication.isPaused)
                return "Paused";

            return "Playing";
        }

        /// <summary>
        /// Get a user-friendly message for a play mode state change.
        /// </summary>
        private static string GetStateMessage(PlayModeStateChange state)
        {
            switch (state)
            {
                case PlayModeStateChange.EnteredEditMode:
                    return "Entered edit mode";
                case PlayModeStateChange.ExitingEditMode:
                    return "Exiting edit mode";
                case PlayModeStateChange.EnteredPlayMode:
                    return "Entered play mode";
                case PlayModeStateChange.ExitingPlayMode:
                    return "Exiting play mode";
                default:
                    return $"State changed to {state}";
            }
        }

        #endregion

        #region Supporting Classes

        /// <summary>
        /// Tracks a pending play mode state change.
        /// </summary>
        private class PendingStateChange
        {
            public string CommandId;
            public string Operation;
            public PlayModeStateChange TargetState;
        }

        #endregion
    }
}

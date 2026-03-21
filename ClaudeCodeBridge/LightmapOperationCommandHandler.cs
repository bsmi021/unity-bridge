using System;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for lightmap baking operations.
    ///
    /// PURPOSE:
    /// Provides Claude Code with the ability to trigger, monitor, and cancel
    /// lightmap bakes, clear baked data, and read current lighting settings.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "bake"     - Start lightmap bake (async or sync-from-Python perspective)
    /// 2. "cancel"   - Cancel in-progress lightmap bake
    /// 3. "clear"    - Clear all baked lightmap data
    /// 4. "status"   - Get current bake status and progress
    /// 5. "settings" - Get current lightmap settings (read-only)
    ///
    /// IMPORTANT: Uses Lightmapping.lightingSettings instead of obsolete
    /// Lightmapping.bakedGI / Lightmapping.realtimeGI properties.
    /// BakeAsync() returns bool -- false means bake cannot start.
    /// </summary>
    public class LightmapOperationCommandHandler : ICommandHandler
    {
        public string CommandType => "lightmap-operation";

        // Deferred bake state for synchronous-from-Python bake requests
        private static string _pendingBakeCommandId;
        private static string _pendingBakeCommandType;
        private static DateTime _bakeStartTime;
        private static float _bakeTimeoutSeconds = 3600f;
        private static bool _callbacksRegistered;

        public LightmapOperationCommandHandler()
        {
            if (!_callbacksRegistered)
            {
                Lightmapping.bakeCompleted += OnBakeCompleted;
                EditorApplication.update += CheckBakeTimeout;
                _callbacksRegistered = true;
            }
        }

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<LightmapOperationParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new LightmapOperationParams();

                BridgeLogger.LogDebug($"Executing lightmap operation: {parameters.operation}");

                switch (parameters.operation?.ToLower())
                {
                    case "bake":
                        return ExecuteBake(command, parameters);
                    case "cancel":
                        return ExecuteCancel(command);
                    case "clear":
                        return ExecuteClear(command);
                    case "status":
                        return ExecuteStatus(command);
                    case "settings":
                        return ExecuteSettings(command);
                    default:
                        return BridgeResponse.Error(
                            command.commandId,
                            command.commandType,
                            $"Unknown lightmap operation: {parameters.operation}. "
                            + "Supported: bake, cancel, clear, status, settings");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Lightmap operation error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse ExecuteBake(BridgeCommand command, LightmapOperationParams parameters)
        {
            if (EditorApplication.isCompiling)
            {
                var errorResult = new LightmapBakeResult
                {
                    operation = "bake",
                    started = false,
                    runAsync = parameters.runAsync,
                    success = false,
                    message = "Cannot bake while Unity is compiling"
                };
                return BridgeResponse.Error(
                    command.commandId, command.commandType, JsonUtility.ToJson(errorResult));
            }

            if (EditorApplication.isPlaying)
            {
                var errorResult = new LightmapBakeResult
                {
                    operation = "bake",
                    started = false,
                    runAsync = parameters.runAsync,
                    success = false,
                    message = "Cannot bake while in Play mode"
                };
                return BridgeResponse.Error(
                    command.commandId, command.commandType, JsonUtility.ToJson(errorResult));
            }

            bool bakeStarted = Lightmapping.BakeAsync();

            if (!bakeStarted)
            {
                var failResult = new LightmapBakeResult
                {
                    operation = "bake",
                    started = false,
                    runAsync = parameters.runAsync,
                    success = false,
                    message = "Lightmap bake failed to start. "
                              + "Check that scenes are loaded and lightmap settings are valid."
                };
                return BridgeResponse.Success(
                    command.commandId, command.commandType, JsonUtility.ToJson(failResult));
            }

            if (parameters.runAsync)
            {
                var asyncResult = new LightmapBakeResult
                {
                    operation = "bake",
                    started = true,
                    runAsync = true,
                    success = true,
                    message = "Lightmap bake started asynchronously"
                };
                return BridgeResponse.Success(
                    command.commandId, command.commandType, JsonUtility.ToJson(asyncResult));
            }

            // Synchronous-from-Python: store pending state and return Running
            _pendingBakeCommandId = command.commandId;
            _pendingBakeCommandType = command.commandType;
            _bakeStartTime = DateTime.UtcNow;

            var runningResult = new LightmapBakeResult
            {
                operation = "bake",
                started = true,
                runAsync = false,
                success = true,
                message = "Lightmap bake started, waiting for completion..."
            };
            return BridgeResponse.Running(
                command.commandId, command.commandType, JsonUtility.ToJson(runningResult));
        }

        private BridgeResponse ExecuteCancel(BridgeCommand command)
        {
            bool wasRunning = Lightmapping.isRunning;
            Lightmapping.Cancel();

            // Clear any pending sync bake
            if (_pendingBakeCommandId is not null)
            {
                _pendingBakeCommandId = null;
            }

            var result = new LightmapCancelResult
            {
                operation = "cancel",
                wasRunning = wasRunning,
                success = true,
                message = wasRunning ? "Lightmap bake cancelled" : "No lightmap bake was running"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteClear(BridgeCommand command)
        {
            if (EditorApplication.isPlaying)
            {
                var errorResult = new LightmapClearResult
                {
                    operation = "clear",
                    success = false,
                    message = "Cannot clear lightmaps while in Play mode"
                };
                return BridgeResponse.Error(
                    command.commandId, command.commandType, JsonUtility.ToJson(errorResult));
            }

            Lightmapping.Clear();

            var result = new LightmapClearResult
            {
                operation = "clear",
                success = true,
                message = "Lightmap data cleared"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteStatus(BridgeCommand command)
        {
            bool isRunning = Lightmapping.isRunning;
            float progress = isRunning ? Lightmapping.buildProgress : 0f;

            string message = isRunning
                ? $"Lightmap bake in progress ({progress * 100:F0}%)"
                : "No lightmap bake in progress";

            var result = new LightmapStatusResult
            {
                operation = "status",
                isRunning = isRunning,
                progress = progress,
                success = true,
                message = message
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteSettings(BridgeCommand command)
        {
            var result = new LightmapSettingsResult
            {
                operation = "settings",
                success = true,
                message = "Lightmap settings retrieved"
            };

            var settings = Lightmapping.lightingSettings;
            if (settings is not null)
            {
                result.lightmapper = settings.lightmapper.ToString();
                result.bakedGI = settings.bakedGI;
                result.realtimeGI = settings.realtimeGI;
                result.directSamples = settings.directSampleCount;
                result.indirectSamples = settings.indirectSampleCount;
                result.environmentSamples = settings.environmentSampleCount;
                result.bounces = settings.maxBounces;
                result.lightmapResolution = settings.lightmapResolution;
                result.lightmapPadding = settings.lightmapPadding;
                result.lightmapMaxSize = settings.lightmapMaxSize;
                result.compressLightmaps = settings.compressLightmaps;
                result.ambientOcclusion = settings.ao;
                result.aoMaxDistance = settings.aoMaxDistance;
                result.directionalMode = settings.directionalityMode.ToString();
                result.mixedBakeMode = settings.mixedBakeMode.ToString();
            }
            else
            {
                result.success = true;
                result.message = "No LightingSettings asset found; using defaults";
            }

            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        // -----------------------------------------------------------------
        // Deferred response callbacks for synchronous bake
        // -----------------------------------------------------------------

        private static void OnBakeCompleted()
        {
            if (_pendingBakeCommandId is null) return;

            var elapsed = (DateTime.UtcNow - _bakeStartTime).TotalSeconds;
            var result = new LightmapBakeResult
            {
                operation = "bake",
                started = true,
                runAsync = false,
                completed = true,
                durationSeconds = elapsed,
                success = true,
                message = $"Lightmap bake completed in {elapsed:F1} seconds"
            };

            WriteDeferredResponse(
                _pendingBakeCommandId, _pendingBakeCommandType, result, isSuccess: true);
            _pendingBakeCommandId = null;
        }

        private static void CheckBakeTimeout()
        {
            if (_pendingBakeCommandId is null) return;

            var elapsed = (DateTime.UtcNow - _bakeStartTime).TotalSeconds;
            if (elapsed < _bakeTimeoutSeconds) return;

            Lightmapping.Cancel();

            var result = new LightmapBakeResult
            {
                operation = "bake",
                started = true,
                runAsync = false,
                completed = false,
                durationSeconds = elapsed,
                success = false,
                message = $"Lightmap bake timed out after {elapsed:F0} seconds"
            };

            WriteDeferredResponse(
                _pendingBakeCommandId, _pendingBakeCommandType, result, isSuccess: false);
            _pendingBakeCommandId = null;
        }

        private static void WriteDeferredResponse(
            string commandId, string commandType, object resultData, bool isSuccess)
        {
            try
            {
                var dataJson = JsonUtility.ToJson(resultData);
                var response = isSuccess
                    ? BridgeResponse.Success(commandId, commandType, dataJson)
                    : BridgeResponse.Error(commandId, commandType, dataJson);

                var projectRoot = System.IO.Directory.GetParent(Application.dataPath).FullName;
                var responsesPath = Path.Combine(
                    projectRoot, ".claude", "unity", "responses");
                var responsePath = Path.Combine(
                    responsesPath, $"{commandId}-{commandType}.json");

                File.WriteAllText(responsePath, JsonUtility.ToJson(response));
                BridgeLogger.LogInfo($"Deferred response written for {commandId}");
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Failed to write deferred response: {ex}");
            }
        }
    }
}

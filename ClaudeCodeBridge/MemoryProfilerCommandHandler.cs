using System;
using System.IO;
using Unity.Profiling.Memory;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for capturing Unity memory snapshots via
    /// Unity.Profiling.Memory.MemoryProfiler.TakeSnapshot.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "take-snapshot" - Capture a .snap file of the current managed/native heap
    ///
    /// TakeSnapshot is async/callback-based: this handler returns a "running"
    /// response immediately, then writes the terminal success/error response
    /// from inside the finishCallback once the snapshot write completes. Unlike
    /// RunTestsCommandHandler, no domain reload occurs mid-capture, so no
    /// SessionState-backed reload survival is needed here.
    /// </summary>
    public class MemoryProfilerCommandHandler : ICommandHandler
    {
        public string CommandType => "memory-profiler";

        private static readonly string PROJECT_ROOT =
            Directory.GetParent(Application.dataPath).FullName;
        private static readonly string SNAPSHOTS_DIR =
            Path.Combine(PROJECT_ROOT, ".claude", "unity", "memory-snapshots");

        private const CaptureFlags DefaultCaptureFlags =
            CaptureFlags.ManagedObjects | CaptureFlags.NativeObjects | CaptureFlags.NativeAllocations;

        private static volatile bool _captureInProgress;

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<MemoryProfilerParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new MemoryProfilerParams();

                BridgeLogger.LogDebug($"Executing memory-profiler operation: {parameters.operation}");

                switch (parameters.operation?.ToLower())
                {
                    case "take-snapshot":
                        return ExecuteTakeSnapshot(command, parameters);
                    default:
                        return BridgeResponse.Error(
                            command.commandId, command.commandType,
                            $"Unknown memory-profiler operation: {parameters.operation}. "
                            + "Supported: take-snapshot");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Memory profiler operation error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse ExecuteTakeSnapshot(BridgeCommand command, MemoryProfilerParams parameters)
        {
            if (_captureInProgress)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "A memory snapshot capture is already in progress");
            }

            CaptureFlags flags;
            try
            {
                flags = ParseCaptureFlags(parameters.captureFlags);
            }
            catch (Exception ex)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Invalid captureFlags: {ex.Message}");
            }

            string path = ResolveSnapshotPath(command.commandId, parameters.path);
            var directory = Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(directory))
                Directory.CreateDirectory(directory);

            _captureInProgress = true;
            string commandId = command.commandId;
            string commandType = command.commandType;

            try
            {
                Unity.Profiling.Memory.MemoryProfiler.TakeSnapshot(
                    path,
                    (savedPath, success) => OnSnapshotFinished(commandId, commandType, savedPath, success),
                    flags);
            }
            catch
            {
                _captureInProgress = false;
                throw;
            }

            var runningResult = new MemoryProfilerResult
            {
                operation = "take-snapshot",
                path = path,
                success = true,
                message = "Memory snapshot capture started"
            };
            return BridgeResponse.Running(
                command.commandId, command.commandType, JsonUtility.ToJson(runningResult));
        }

        private static void OnSnapshotFinished(
            string commandId, string commandType, string savedPath, bool success)
        {
            try
            {
                var result = new MemoryProfilerResult
                {
                    operation = "take-snapshot",
                    path = savedPath,
                    success = success,
                    message = success
                        ? $"Memory snapshot saved to {savedPath}"
                        : "Memory snapshot capture failed"
                };

                var response = success
                    ? BridgeResponse.Success(commandId, commandType, JsonUtility.ToJson(result))
                    : BridgeResponse.Error(commandId, commandType, "Snapshot capture failed");

                ClaudeUnityBridge.WriteResponseStatic(response);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Failed to write memory-profiler response: {ex}");
            }
            finally
            {
                _captureInProgress = false;
            }
        }

        private static string ResolveSnapshotPath(string commandId, string requestedPath)
        {
            if (!string.IsNullOrEmpty(requestedPath))
                return requestedPath;

            return Path.Combine(SNAPSHOTS_DIR, $"{commandId}.snap");
        }

        private static CaptureFlags ParseCaptureFlags(string captureFlagsCsv)
        {
            if (string.IsNullOrEmpty(captureFlagsCsv))
                return DefaultCaptureFlags;

            CaptureFlags combined = 0;
            var names = captureFlagsCsv.Split(',');
            foreach (var rawName in names)
            {
                var name = rawName.Trim();
                if (name.Length == 0)
                    continue;

                combined |= (CaptureFlags)Enum.Parse(typeof(CaptureFlags), name, ignoreCase: true);
            }

            return combined;
        }
    }
}

using System;
using UnityEditor;
using UnityEditorInternal;
using UnityEngine;
using UnityEngine.Profiling;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for advanced profiler controls.
    ///
    /// PURPOSE:
    /// Start/stop profiling, save profiler data to file, and query
    /// detailed memory statistics.
    ///
    /// COMMAND JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "profiler-control",
    ///   "parametersJson": "{\"operation\":\"start\"}"
    /// }
    /// </summary>
    public class ProfilerControlCommandHandler : ICommandHandler
    {
        public string CommandType => "profiler-control";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<ProfilerControlParams>(
                    command.parametersJson ?? "{}");

                if (parameters == null
                    || string.IsNullOrEmpty(parameters.operation))
                {
                    return BridgeResponse.Error(
                        command.commandId, command.commandType,
                        "Missing required parameter: operation");
                }

                ProfilerControlResult result;
                switch (parameters.operation.ToLower())
                {
                    case "start":
                        result = StartProfiling(parameters);
                        break;
                    case "stop":
                        result = StopProfiling();
                        break;
                    case "save":
                        result = SaveProfilerData(parameters);
                        break;
                    case "memory":
                        result = GetMemoryStats();
                        break;
                    case "set-areas":
                        result = SetAreas(parameters);
                        break;
                    default:
                        return BridgeResponse.Error(
                            command.commandId, command.commandType,
                            $"Unknown operation: {parameters.operation}. "
                            + "Supported: start, stop, save, memory, set-areas");
                }

                if (result.success)
                {
                    BridgeLogger.LogInfo(
                        $"profiler-control {parameters.operation}: "
                        + result.message);
                    return BridgeResponse.Success(
                        command.commandId, command.commandType,
                        JsonUtility.ToJson(result));
                }
                return BridgeResponse.Error(
                    command.commandId, command.commandType, result.message);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error: {ex}");
                return BridgeResponse.Error(
                    command.commandId, command.commandType, ex.ToString());
            }
        }

        private ProfilerControlResult StartProfiling(
            ProfilerControlParams parameters)
        {
            var result = new ProfilerControlResult { operation = "start" };

            try
            {
                if (!string.IsNullOrEmpty(parameters.logFile))
                {
                    Profiler.logFile = parameters.logFile;
                    Profiler.enableBinaryLog = true;
                }

                ProfilerFrameCommandHandler.StartExternalCapture();
                ProfilerDriver.profileEditor = true;
                ProfilerDriver.enabled = true;
                Profiler.enabled = true;

                result.success = true;
                result.profilerEnabled = true;
                result.logFile = Profiler.logFile;
                result.message = "Profiler started";
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to start profiler: {ex.Message}";
            }

            return result;
        }

        private ProfilerControlResult StopProfiling()
        {
            var result = new ProfilerControlResult { operation = "stop" };

            try
            {
                Profiler.enabled = false;
                ProfilerDriver.enabled = false;
                Profiler.enableBinaryLog = false;
                ProfilerFrameCommandHandler.StopExternalCapture();

                result.success = true;
                result.profilerEnabled = false;
                result.message = "Profiler stopped";
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to stop profiler: {ex.Message}";
            }

            return result;
        }

        private ProfilerControlResult SaveProfilerData(
            ProfilerControlParams parameters)
        {
            var result = new ProfilerControlResult { operation = "save" };

            if (string.IsNullOrEmpty(parameters.logFile))
            {
                result.success = false;
                result.message = "logFile is required for save operation";
                return result;
            }

            try
            {
                // Set the log file path and enable binary logging
                Profiler.logFile = parameters.logFile;
                Profiler.enableBinaryLog = true;

                ProfilerFrameCommandHandler.StartExternalCapture();
                ProfilerDriver.profileEditor = true;
                ProfilerDriver.enabled = true;
                Profiler.enabled = true;

                result.success = true;
                result.profilerEnabled = Profiler.enabled || ProfilerDriver.enabled;
                result.logFile = parameters.logFile;
                result.message = $"Profiler data will be saved to: "
                    + parameters.logFile;
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to save profiler data: {ex.Message}";
            }

            return result;
        }

        private ProfilerControlResult GetMemoryStats()
        {
            var result = new ProfilerControlResult { operation = "memory" };

            try
            {
                result.totalAllocatedMB =
                    Profiler.GetTotalAllocatedMemoryLong() / (1024L * 1024L);
                result.totalReservedMB =
                    Profiler.GetTotalReservedMemoryLong() / (1024L * 1024L);
                result.monoHeapMB =
                    Profiler.GetMonoHeapSizeLong() / (1024L * 1024L);
                result.monoUsedMB =
                    Profiler.GetMonoUsedSizeLong() / (1024L * 1024L);
                result.graphicsDriverMB =
                    Profiler.GetAllocatedMemoryForGraphicsDriver()
                    / (1024L * 1024L);
                result.tempAllocatorMB =
                    Profiler.GetTempAllocatorSize() / (1024L * 1024L);
                result.profilerEnabled = Profiler.enabled || ProfilerDriver.enabled;

                result.success = true;
                result.message = $"Total allocated: {result.totalAllocatedMB}MB, "
                    + $"Mono heap: {result.monoHeapMB}MB, "
                    + $"GFX: {result.graphicsDriverMB}MB";
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to get memory stats: {ex.Message}";
            }

            return result;
        }

        private ProfilerControlResult SetAreas(ProfilerControlParams parameters)
        {
            var result = new ProfilerControlResult { operation = "set-areas" };
            try
            {
                if (!string.IsNullOrEmpty(parameters.areas))
                {
                    foreach (var areaName in parameters.areas.Split(','))
                    {
                        if (Enum.TryParse(areaName.Trim(), true, out ProfilerArea area))
                        {
                            ProfilerDriver.SetAreaEnabled(area, parameters.enabled);
                            result.areas = AppendArea(result.areas, area.ToString());
                        }
                    }
                }

                if (parameters.allocationCallstacks)
                    Profiler.enableAllocationCallstacks = true;
                result.allocationCallstacks = Profiler.enableAllocationCallstacks;
                result.success = true;
                result.message = "Profiler areas updated";
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to set profiler areas: {ex.Message}";
            }
            return result;
        }

        private static string AppendArea(string current, string area)
        {
            return string.IsNullOrEmpty(current) ? area : current + "," + area;
        }
    }

    [Serializable]
    public class ProfilerControlParams
    {
        public string operation;
        public string logFile;
        public string areas;
        public bool enabled = true;
        public bool allocationCallstacks;
    }

    [Serializable]
    public class ProfilerControlResult
    {
        public string operation;
        public bool profilerEnabled;
        public string logFile;
        public long totalAllocatedMB;
        public long totalReservedMB;
        public long monoHeapMB;
        public long monoUsedMB;
        public long graphicsDriverMB;
        public long tempAllocatorMB;
        public string areas;
        public bool allocationCallstacks;
        public bool success;
        public string message;
    }
}

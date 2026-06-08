using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.Profiling;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for capturing Unity Profiler performance snapshots.
    ///
    /// PURPOSE:
    /// Captures real-time performance metrics from Unity's Profiler, enabling
    /// automated performance monitoring, regression detection, and optimization
    /// validation without manual Profiler window inspection.
    ///
    /// USE CASES:
    /// - Automated performance regression testing
    /// - Memory leak detection in automated tests
    /// - Continuous performance monitoring in CI/CD
    /// - Optimization validation (before/after comparisons)
    /// - Performance baseline establishment
    ///
    /// COMMAND JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "profiler-sample",
    ///   "timestamp": "2025-10-05T18:00:00Z",
    ///   "parametersJson": "{\"includeMemory\":true,\"includeRendering\":true,\"includePhysics\":false}"
    /// }
    ///
    /// USAGE EXAMPLES:
    ///
    /// 1. Full performance snapshot:
    ///    send-command.ps1 -CommandType "profiler-sample" -Parameters @{includeMemory=$true; includeRendering=$true; includePhysics=$true}
    ///
    /// 2. Memory-only snapshot:
    ///    send-command.ps1 -CommandType "profiler-sample" -Parameters @{includeMemory=$true; includeRendering=$false}
    ///
    /// 3. Quick rendering check:
    ///    send-command.ps1 -CommandType "profiler-sample" -Parameters @{includeRendering=$true}
    ///
    /// NOTE: More accurate results are obtained when running in Play Mode.
    /// </summary>
    public class ProfilerSampleCommandHandler : ICommandHandler
    {
        public string CommandType => "profiler-sample";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<ProfilerSampleParams>(command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new ProfilerSampleParams();

                BridgeLogger.LogDebug($"Capturing profiler snapshot");

                var result = new ProfilerSampleResult();

                // Capture memory data
                if (parameters.includeMemory)
                {
                    result.totalMemoryMB = Profiler.GetTotalReservedMemoryLong() / (1024 * 1024);
                    result.monoMemoryMB = Profiler.GetMonoUsedSizeLong() / (1024 * 1024);

                    // Graphics memory (approximation)
                    result.graphicsMemoryMB = Profiler.GetAllocatedMemoryForGraphicsDriver() / (1024 * 1024);
                }

                // Capture rendering data
                if (parameters.includeRendering)
                {
#if UNITY_EDITOR
                    // Use UnityStats for rendering info.
                    result.triangles = UnityStats.triangles;
                    result.drawCalls = UnityStats.drawCalls;
                    result.vertices = UnityStats.vertices;
#endif
                }

                // Frame time
                result.lastFrameTime = Time.deltaTime * 1000f; // Convert to ms

                // Get top memory allocators (simplified)
                if (parameters.includeMemory)
                {
                    result.topAllocators = GetTopMemoryAllocators();
                }

                var resultJson = JsonUtility.ToJson(result);
                BridgeLogger.LogInfo($"Snapshot captured: {result.totalMemoryMB}MB total, {result.drawCalls} draw calls");

                return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        /// <summary>
        /// Get simplified list of top memory allocators.
        /// </summary>
        private List<string> GetTopMemoryAllocators()
        {
            var allocators = new List<string>();

            try
            {
                // Add basic memory categories
                var totalMem = Profiler.GetTotalReservedMemoryLong();
                var monoMem = Profiler.GetMonoUsedSizeLong();
                var gfxMem = Profiler.GetAllocatedMemoryForGraphicsDriver();

                if (monoMem > 0)
                    allocators.Add($"Managed Heap: {monoMem / (1024 * 1024)}MB");
                if (gfxMem > 0)
                    allocators.Add($"Graphics: {gfxMem / (1024 * 1024)}MB");

                var otherMem = totalMem - monoMem - gfxMem;
                if (otherMem > 0)
                    allocators.Add($"Native/Other: {otherMem / (1024 * 1024)}MB");
            }
            catch (Exception ex)
            {
                BridgeLogger.LogWarning($"Could not get detailed allocators: {ex.Message}");
            }

            return allocators;
        }
    }
}

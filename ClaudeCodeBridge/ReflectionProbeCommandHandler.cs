using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for reflection probe operations.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "bake"     - Bake a single reflection probe by name/path
    /// 2. "bake-all" - Bake all reflection probes in the scene
    /// 3. "list"     - List all reflection probes in the scene
    /// 4. "get-info" - Get probe settings (resolution, mode, bounds, etc.)
    /// </summary>
    public class ReflectionProbeCommandHandler : ICommandHandler
    {
        public string CommandType => "reflection-probe";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Cannot perform reflection probe operations while scripts are compiling.");
                }

                var parameters = JsonUtility.FromJson<ReflectionProbeParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new ReflectionProbeParams();

                BridgeLogger.LogDebug($"Executing reflection-probe operation: {parameters.operation}");

                switch (parameters.operation?.ToLower())
                {
                    case "bake":
                        return ExecuteBake(command, parameters);
                    case "bake-all":
                        return ExecuteBakeAll(command);
                    case "list":
                        return ExecuteList(command);
                    case "get-info":
                        return ExecuteGetInfo(command, parameters);
                    default:
                        return BridgeResponse.Error(
                            command.commandId, command.commandType,
                            $"Unknown reflection-probe operation: {parameters.operation}. "
                            + "Supported: bake, bake-all, list, get-info");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"ReflectionProbe operation error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse ExecuteBake(BridgeCommand command, ReflectionProbeParams p)
        {
            if (EditorApplication.isPlaying)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "Cannot bake reflection probes while in Play mode.");
            }

            ReflectionProbe probe = FindProbe(p.gameObjectPath);
            if (probe is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"ReflectionProbe not found: {p.gameObjectPath ?? "(none)"}");
            }

            probe.RenderProbe();

            var result = new ReflectionProbeResult
            {
                operation = "bake",
                probeName = probe.gameObject.name,
                success = true,
                message = $"Reflection probe '{probe.gameObject.name}' baked"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteBakeAll(BridgeCommand command)
        {
            if (EditorApplication.isPlaying)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "Cannot bake reflection probes while in Play mode.");
            }

            var probes = UnityEngine.Object.FindObjectsByType<ReflectionProbe>(
                FindObjectsSortMode.None);
            int count = 0;
            foreach (var probe in probes)
            {
                probe.RenderProbe();
                count++;
            }

            var result = new ReflectionProbeResult
            {
                operation = "bake-all",
                probeCount = count,
                success = true,
                message = $"Baked {count} reflection probes"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteList(BridgeCommand command)
        {
            var probes = UnityEngine.Object.FindObjectsByType<ReflectionProbe>(
                FindObjectsSortMode.None);
            var probeInfos = new List<ReflectionProbeInfo>();

            foreach (var probe in probes)
            {
                probeInfos.Add(new ReflectionProbeInfo
                {
                    gameObjectPath = GetHierarchyPath(probe.gameObject),
                    mode = probe.mode.ToString(),
                    resolution = probe.resolution,
                    intensity = probe.intensity,
                    boxProjection = probe.boxProjection
                });
            }

            var result = new ReflectionProbeListResult
            {
                operation = "list",
                probes = probeInfos,
                success = true,
                message = $"Found {probeInfos.Count} reflection probes"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteGetInfo(BridgeCommand command, ReflectionProbeParams p)
        {
            ReflectionProbe probe = FindProbe(p.gameObjectPath);
            if (probe is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"ReflectionProbe not found: {p.gameObjectPath ?? "(none)"}");
            }

            var result = new ReflectionProbeDetailResult
            {
                operation = "get-info",
                gameObjectPath = GetHierarchyPath(probe.gameObject),
                mode = probe.mode.ToString(),
                resolution = probe.resolution,
                intensity = probe.intensity,
                boxProjection = probe.boxProjection,
                boundsCenter = $"{probe.bounds.center.x},{probe.bounds.center.y},{probe.bounds.center.z}",
                boundsSize = $"{probe.bounds.size.x},{probe.bounds.size.y},{probe.bounds.size.z}",
                refreshMode = probe.refreshMode.ToString(),
                timeSlicingMode = probe.timeSlicingMode.ToString(),
                success = true,
                message = "Reflection probe info retrieved"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        // -----------------------------------------------------------------
        // Helpers
        // -----------------------------------------------------------------

        private static ReflectionProbe FindProbe(string path)
        {
            if (string.IsNullOrEmpty(path)) return null;
            var go = GameObject.Find(path);
            if (go is null) return null;
            return go.GetComponent<ReflectionProbe>();
        }

        private static string GetHierarchyPath(GameObject go)
        {
            string path = go.name;
            var parent = go.transform.parent;
            while (parent is not null)
            {
                path = parent.name + "/" + path;
                parent = parent.parent;
            }
            return path;
        }
    }

    // -----------------------------------------------------------------
    // Models
    // -----------------------------------------------------------------

    [Serializable]
    public class ReflectionProbeParams
    {
        public string operation;
        public string gameObjectPath;
    }

    [Serializable]
    public class ReflectionProbeResult
    {
        public string operation;
        public string probeName;
        public int probeCount;
        public bool success;
        public string message;
    }

    [Serializable]
    public class ReflectionProbeInfo
    {
        public string gameObjectPath;
        public string mode;
        public int resolution;
        public float intensity;
        public bool boxProjection;
    }

    [Serializable]
    public class ReflectionProbeListResult
    {
        public string operation;
        public List<ReflectionProbeInfo> probes = new List<ReflectionProbeInfo>();
        public bool success;
        public string message;
    }

    [Serializable]
    public class ReflectionProbeDetailResult
    {
        public string operation;
        public string gameObjectPath;
        public string mode;
        public int resolution;
        public float intensity;
        public bool boxProjection;
        public string boundsCenter;
        public string boundsSize;
        public string refreshMode;
        public string timeSlicingMode;
        public bool success;
        public string message;
    }
}

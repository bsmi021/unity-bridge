using System;
using System.Collections.Generic;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Parameters for the lightmap-operation command.
    /// Supports: bake, cancel, clear, status, settings.
    /// </summary>
    [Serializable]
    public class LightmapOperationParams
    {
        public string operation; // "bake", "cancel", "clear", "status", "settings"
        public bool runAsync = true; // For bake: return immediately or wait for completion
    }

    /// <summary>
    /// Result data for lightmap bake operation.
    /// </summary>
    [Serializable]
    public class LightmapBakeResult
    {
        public string operation;
        public bool started;
        public bool runAsync;
        public bool completed;
        public double durationSeconds;
        public bool success;
        public string message;
    }

    /// <summary>
    /// Result data for lightmap cancel operation.
    /// </summary>
    [Serializable]
    public class LightmapCancelResult
    {
        public string operation;
        public bool wasRunning;
        public bool success;
        public string message;
    }

    /// <summary>
    /// Result data for lightmap clear operation.
    /// </summary>
    [Serializable]
    public class LightmapClearResult
    {
        public string operation;
        public bool success;
        public string message;
    }

    /// <summary>
    /// Result data for lightmap status operation.
    /// </summary>
    [Serializable]
    public class LightmapStatusResult
    {
        public string operation;
        public bool isRunning;
        public float progress;
        public bool success;
        public string message;
    }

    /// <summary>
    /// Result data for lightmap settings operation (read-only).
    /// Uses LightingSettings asset instead of obsolete Lightmapping static properties.
    /// </summary>
    [Serializable]
    public class LightmapSettingsResult
    {
        public string operation;
        public string lightmapper;
        public bool bakedGI;
        public bool realtimeGI;
        public int directSamples;
        public int indirectSamples;
        public int environmentSamples;
        public int bounces;
        public float lightmapResolution;
        public int lightmapPadding;
        public int lightmapMaxSize;
        public bool compressLightmaps;
        public bool ambientOcclusion;
        public float aoMaxDistance;
        public string directionalMode;
        public string mixedBakeMode;
        public bool success;
        public string message;
    }
}

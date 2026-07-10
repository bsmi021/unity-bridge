using System;
using System.IO;
using UnityEditor;
using UnityEditor.Compilation;
using UnityEditor.SceneManagement;
#if UNITY_6000_5_OR_NEWER
using Unity.Scripting.LifecycleManagement;
using UnityEditor.Scripting.LifecycleManagement;
#endif
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Generates periodic heartbeat files for bridge health monitoring.
    ///
    /// PURPOSE:
    /// Writes periodic health status files to enable Claude Code to monitor
    /// the bridge's health without relying on timeouts. Heartbeats include
    /// Unity state information (version, play mode, compilation status, etc.)
    /// and can be checked by the Python health monitor.
    ///
    /// TECHNICAL DETAILS:
    /// - Initialized via [InitializeOnLoad] attribute (runs on editor startup)
    /// - Writes heartbeat every 5 seconds to .claude/unity/heartbeat.json
    /// - Uses atomic writes (write to .tmp then rename) to prevent corruption
    /// - Tracks command count for monitoring throughput
    /// - Lightweight implementation to avoid performance impact
    ///
    /// HEARTBEAT FILE FORMAT:
    /// {
    ///   "timestamp": "2025-01-06T18:00:00.000Z",
    ///   "unityVersion": "6000.2.7f2",
    ///   "isCompiling": false,
    ///   "isPlaying": false,
    ///   "isPaused": false,
    ///   "activeScene": "GameplayScene",
    ///   "commandsProcessed": 42,
    ///   "uptimeSeconds": 3600
    /// }
    ///
    /// MONITORING:
    /// Python's health_monitor.py reads this file to determine bridge health.
    /// Heartbeat staleness (>15 seconds old) indicates the bridge is frozen or closed.
    /// </summary>
    [InitializeOnLoad]
    public partial class HeartbeatGenerator
    {
        // Heartbeat write intervals in seconds
        private const float IDLE_HEARTBEAT_INTERVAL = 5.0f;
        private const float BUSY_HEARTBEAT_INTERVAL = 1.0f;

        private static float _lastHeartbeatTime = 0f;
        private static string _heartbeatPath;
        private static long _startTime;
        private static int _commandsProcessed = 0;
        private static string _lastReloadTimestamp;
        private static bool _isReloadingAssemblies = false;
        private static bool _isPlayModeTransition = false;
        private static string _lastBusyReason;
        private static string _lastBusyTimestamp;

        public static int DomainGeneration { get; private set; }

        /// <summary>
        /// Static constructor - runs when editor loads.
        /// Initializes heartbeat system and registers for updates.
        /// </summary>
        static HeartbeatGenerator()
        {
            try
            {
                // Record start time for uptime calculation
                _startTime = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
                DomainGeneration = SessionState.GetInt("UnityBridge.DomainGeneration", 0) + 1;
                SessionState.SetInt("UnityBridge.DomainGeneration", DomainGeneration);
                _lastReloadTimestamp = DateTime.UtcNow.ToString("o");
                SessionState.SetString("UnityBridge.LastReloadTimestamp", _lastReloadTimestamp);

                // Find bridge directory (.claude/unity/)
                var projectRoot = Directory.GetParent(Application.dataPath).FullName;
                var bridgeDir = Path.Combine(projectRoot, ".claude", "unity");
                _heartbeatPath = Path.Combine(bridgeDir, "heartbeat.json");

                // Ensure directory exists
                Directory.CreateDirectory(bridgeDir);

                // Register for editor updates (called every frame)
                EditorApplication.update += OnEditorUpdate;
                RegisterBusyTracking();

                // Write initial heartbeat immediately
                WriteHeartbeat();

                BridgeLogger.LogInfo("HeartbeatGenerator initialized - heartbeat file: " + _heartbeatPath);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"HeartbeatGenerator failed to initialize: {ex}");
            }
        }

        /// <summary>
        /// Called every editor frame.
        /// Writes heartbeat at regular intervals.
        /// </summary>
        private static void OnEditorUpdate()
        {
            try
            {
                float currentTime = (float)EditorApplication.timeSinceStartup;
                float interval = IsEditorBusy()
                    ? BUSY_HEARTBEAT_INTERVAL
                    : IDLE_HEARTBEAT_INTERVAL;

                // Write heartbeat if interval elapsed
                if (currentTime - _lastHeartbeatTime >= interval)
                {
                    WriteHeartbeat();
                    _lastHeartbeatTime = currentTime;
                }
            }
            catch (Exception ex)
            {
                // Log error only occasionally to avoid spam
                if (_commandsProcessed % 100 == 0)
                {
                    BridgeLogger.LogWarning($"HeartbeatGenerator error in update: {ex.Message}");
                }
            }
        }

        /// <summary>
        /// Increments the command count.
        /// Called by command handlers to track throughput.
        /// </summary>
        public static void IncrementCommandCount()
        {
            _commandsProcessed++;
        }

        private static void RegisterBusyTracking()
        {
            CompilationPipeline.compilationStarted += _ => MarkBusy("compiling");
            CompilationPipeline.compilationFinished += _ => MarkBusy("compiling");
            AssemblyReloadEvents.beforeAssemblyReload += MarkAssemblyReloadStarting;
            AssemblyReloadEvents.afterAssemblyReload += MarkAssemblyReloadFinished;
            EditorApplication.playModeStateChanged += OnPlayModeStateChanged;
        }

#if UNITY_6000_5_OR_NEWER
        [OnCodeUnloading]
        private static void OnUnity65CodeUnloading()
        {
            MarkAssemblyReloadStarting();
        }

        [OnCodeLoaded]
        private static void OnUnity65CodeLoaded()
        {
            MarkAssemblyReloadFinished();
        }

        [OnEnteringEditMode]
        private static void OnUnity65EnteringEditMode()
        {
            SetPlayModeTransition(false);
        }

        [OnExitingEditMode]
        private static void OnUnity65ExitingEditMode()
        {
            SetPlayModeTransition(true);
        }

        [OnEnteringPlayMode]
        private static void OnUnity65EnteringPlayMode()
        {
            SetPlayModeTransition(false);
        }

        [OnExitingPlayMode]
        private static void OnUnity65ExitingPlayMode()
        {
            SetPlayModeTransition(true);
        }
#endif

        private static void MarkAssemblyReloadStarting()
        {
            _isReloadingAssemblies = true;
            MarkBusy("reloading_assemblies");
            WriteHeartbeat();
        }

        private static void MarkAssemblyReloadFinished()
        {
            _isReloadingAssemblies = false;
            MarkBusy("reloading_assemblies");
            WriteHeartbeat();
        }

        private static void OnPlayModeStateChanged(PlayModeStateChange state)
        {
            SetPlayModeTransition(
                state == PlayModeStateChange.ExitingEditMode
                || state == PlayModeStateChange.ExitingPlayMode);
        }

        private static void SetPlayModeTransition(bool active)
        {
            _isPlayModeTransition = active;
            if (active)
                MarkBusy("playmode_transition");
            WriteHeartbeat();
        }

        private static bool IsEditorBusy()
        {
            return EditorApplication.isCompiling
                || EditorApplication.isUpdating
                || _isReloadingAssemblies
                || _isPlayModeTransition;
        }

        private static string GetCurrentBusyReason()
        {
            if (EditorApplication.isCompiling) return "compiling";
            if (EditorApplication.isUpdating) return "updating";
            if (_isReloadingAssemblies) return "reloading_assemblies";
            if (_isPlayModeTransition) return "playmode_transition";
            return null;
        }

        private static void MarkBusy(string reason)
        {
            _lastBusyReason = reason;
            _lastBusyTimestamp = DateTime.UtcNow.ToString("o");
        }

        /// <summary>
        /// Writes the current heartbeat to the heartbeat file.
        /// Uses atomic writes to prevent corruption.
        /// </summary>
        private static void WriteHeartbeat()
        {
            try
            {
                string busyReason = GetCurrentBusyReason();
                if (!string.IsNullOrEmpty(busyReason))
                {
                    MarkBusy(busyReason);
                }

                // Build heartbeat data
                var heartbeat = new Heartbeat
                {
                    timestamp = DateTime.UtcNow.ToString("o"),
                    unityVersion = Application.unityVersion,
                    isCompiling = EditorApplication.isCompiling,
                    isUpdating = EditorApplication.isUpdating,
                    isReloadingAssemblies = _isReloadingAssemblies,
                    isPlayingOrWillChangePlaymode = _isPlayModeTransition,
                    busyReason = busyReason,
                    lastBusyReason = _lastBusyReason,
                    lastBusyTimestamp = _lastBusyTimestamp,
                    domainGeneration = DomainGeneration,
                    lastReloadTimestamp = _lastReloadTimestamp,
                    isPlaying = EditorApplication.isPlaying,
                    isPaused = EditorApplication.isPaused,
                    activeScene = EditorSceneManager.GetActiveScene().name,
                    commandsProcessed = _commandsProcessed,
                    uptimeSeconds = DateTimeOffset.UtcNow.ToUnixTimeSeconds() - _startTime
                };

                // Convert to JSON
                var json = JsonUtility.ToJson(heartbeat, prettyPrint: true);

                // Atomic write via the shared helper (temp file + fsync + replace
                // with bounded retries). The previous delete-then-move left a
                // window where a health check could observe no heartbeat file.
                BridgeOperationLedger.WriteAtomic(_heartbeatPath, json);
            }
            catch (Exception ex)
            {
                // Log error only occasionally to avoid console spam
                if (_commandsProcessed % 100 == 0)
                {
                    BridgeLogger.LogWarning($"HeartbeatGenerator failed to write heartbeat: {ex.Message}");
                }
            }
        }

        /// <summary>
        /// Heartbeat data structure.
        /// Serializable format for JSON output.
        /// </summary>
        [System.Serializable]
        private class Heartbeat
        {
            // ISO 8601 timestamp of heartbeat generation
            public string timestamp;

            // Unity version string (e.g., "6000.2.7f2")
            public string unityVersion;

            // Whether Unity is currently compiling scripts
            public bool isCompiling;

            // Whether AssetDatabase refresh/import is active
            public bool isUpdating;

            // Whether Unity is in an assembly reload window
            public bool isReloadingAssemblies;

            // Whether play mode is entering or exiting
            public bool isPlayingOrWillChangePlaymode;

            // Current editor busy reason, null when command-ready
            public string busyReason;

            // Last observed editor busy reason
            public string lastBusyReason;

            // ISO 8601 timestamp for the last observed editor busy state
            public string lastBusyTimestamp;

            // Monotonic domain generation for this editor session
            public int domainGeneration;

            // ISO 8601 timestamp for the last bridge domain load
            public string lastReloadTimestamp;

            // Whether editor is in play mode
            public bool isPlaying;

            // Whether play mode is paused
            public bool isPaused;

            // Name of currently active scene
            public string activeScene;

            // Total number of commands processed since editor started
            public int commandsProcessed;

            // Seconds since bridge generator was initialized
            public long uptimeSeconds;
        }
    }
}

using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
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
    public class HeartbeatGenerator
    {
        // Heartbeat write interval in seconds
        private const float HEARTBEAT_INTERVAL = 5.0f;

        private static float _lastHeartbeatTime = 0f;
        private static string _heartbeatPath;
        private static long _startTime;
        private static int _commandsProcessed = 0;

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

                // Find bridge directory (.claude/unity/)
                var projectRoot = Directory.GetParent(Application.dataPath).FullName;
                var bridgeDir = Path.Combine(projectRoot, ".claude", "unity");
                _heartbeatPath = Path.Combine(bridgeDir, "heartbeat.json");

                // Ensure directory exists
                Directory.CreateDirectory(bridgeDir);

                // Register for editor updates (called every frame)
                EditorApplication.update += OnEditorUpdate;

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

                // Write heartbeat if interval elapsed
                if (currentTime - _lastHeartbeatTime >= HEARTBEAT_INTERVAL)
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

        /// <summary>
        /// Writes the current heartbeat to the heartbeat file.
        /// Uses atomic writes to prevent corruption.
        /// </summary>
        private static void WriteHeartbeat()
        {
            try
            {
                // Build heartbeat data
                var heartbeat = new Heartbeat
                {
                    timestamp = DateTime.UtcNow.ToString("o"),
                    unityVersion = Application.unityVersion,
                    isCompiling = EditorApplication.isCompiling,
                    isPlaying = EditorApplication.isPlaying,
                    isPaused = EditorApplication.isPaused,
                    activeScene = EditorSceneManager.GetActiveScene().name,
                    commandsProcessed = _commandsProcessed,
                    uptimeSeconds = DateTimeOffset.UtcNow.ToUnixTimeSeconds() - _startTime
                };

                // Convert to JSON
                var json = JsonUtility.ToJson(heartbeat, prettyPrint: true);

                // Atomic write: write to temp file first, then rename
                var tempPath = _heartbeatPath + ".tmp";
                File.WriteAllText(tempPath, json);

                // Rename (atomic on most filesystems)
                if (File.Exists(_heartbeatPath))
                {
                    File.Delete(_heartbeatPath);
                }
                File.Move(tempPath, _heartbeatPath);
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

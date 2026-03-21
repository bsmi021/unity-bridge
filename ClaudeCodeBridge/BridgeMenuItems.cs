using System;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Unity Editor menu items for ClaudeUnityBridge.
    /// Extracted from ClaudeUnityBridge to keep it under 500 LOC.
    /// </summary>
    public static class BridgeMenuItems
    {
        private static readonly string PROJECT_ROOT = Directory.GetParent(Application.dataPath).FullName;
        private static readonly string COMMANDS_PATH = Path.Combine(PROJECT_ROOT, ".claude", "unity", "commands");
        private static readonly string RESPONSES_PATH = Path.Combine(PROJECT_ROOT, ".claude", "unity", "responses");

        #region Assets Menu Items

        [MenuItem("Assets/Claude Code Bridge/Test Connection", false, 100)]
        public static void TestConnection()
        {
            Debug.Log("[ClaudeUnityBridge] Testing bridge connection...");

            try
            {
                var status = ClaudeUnityBridge.GetBridgeStatus();
                if (status.isHealthy)
                {
                    Debug.Log($"[ClaudeUnityBridge] Connection successful!\n" +
                             $"- Bridge initialized: {status.isInitialized}\n" +
                             $"- File watcher active: {status.isWatcherActive}\n" +
                             $"- Registered handlers: {status.handlerCount}\n" +
                             $"- Commands processed: {status.processedCount}");
                }
                else
                {
                    Debug.LogWarning("[ClaudeUnityBridge] Bridge is not fully operational. Attempting to reinitialize...");
                    ClaudeUnityBridge.ForceReinitialize();
                    var refreshed = ClaudeUnityBridge.GetBridgeStatus();
                    if (refreshed.isInitialized)
                    {
                        Debug.Log("[ClaudeUnityBridge] Bridge reinitialized successfully!");
                    }
                    else
                    {
                        Debug.LogError("[ClaudeUnityBridge] Failed to initialize bridge. Check console for errors.");
                    }
                }
            }
            catch (Exception ex)
            {
                Debug.LogError($"[ClaudeUnityBridge] Connection test failed: {ex}");
            }
        }

        [MenuItem("Assets/Claude Code Bridge/Show Status", false, 101)]
        public static void ShowStatusFromAssetsMenu()
        {
            ShowStatus();
        }

        [MenuItem("Assets/Claude Code Bridge/Clean Old Responses", false, 200)]
        public static void CleanOldResponsesFromAssetsMenu()
        {
            CleanOldResponses();
        }

        [MenuItem("Assets/Claude Code Bridge/Clean Old Commands", false, 201)]
        public static void CleanOldCommands()
        {
            try
            {
                var cutoffTime = DateTime.UtcNow.AddHours(-1);
                var files = Directory.GetFiles(COMMANDS_PATH, "*.json");
                int cleaned = 0;

                foreach (var file in files)
                {
                    if (File.GetCreationTimeUtc(file) < cutoffTime)
                    {
                        File.Delete(file);
                        cleaned++;
                    }
                }

                Debug.Log($"[ClaudeUnityBridge] Cleaned {cleaned} old command files");
            }
            catch (Exception ex)
            {
                Debug.LogError($"[ClaudeUnityBridge] Error cleaning commands: {ex}");
            }
        }

        [MenuItem("Assets/Claude Code Bridge/Reset Bridge", false, 300)]
        public static void ResetBridgeFromAssetsMenu()
        {
            ResetBridge();
        }

        [MenuItem("Assets/Claude Code Bridge/Open Documentation", false, 400)]
        public static void OpenDocumentation()
        {
            Application.OpenURL("https://github.com/anthropics/claude-code");
            Debug.Log("[ClaudeUnityBridge] Opening documentation in browser...");
        }

        [MenuItem("Assets/Claude Code Bridge/Show File Paths", false, 401)]
        public static void ShowFilePaths()
        {
            Debug.Log($"[ClaudeUnityBridge] File System Paths:\n" +
                     $"Commands: {COMMANDS_PATH}\n" +
                     $"Responses: {RESPONSES_PATH}\n" +
                     $"Project Root: {PROJECT_ROOT}");
        }

        #endregion

        #region Tools Menu Items

        [MenuItem("Tools/Claude Code Bridge/Clean Old Responses")]
        public static void CleanOldResponses()
        {
            try
            {
                var cutoffTime = DateTime.UtcNow.AddHours(-1);
                var files = Directory.GetFiles(RESPONSES_PATH, "*.json");
                int cleaned = 0;

                foreach (var file in files)
                {
                    if (File.GetCreationTimeUtc(file) < cutoffTime)
                    {
                        File.Delete(file);
                        cleaned++;
                    }
                }

                Debug.Log($"[ClaudeUnityBridge] Cleaned {cleaned} old response files");
            }
            catch (Exception ex)
            {
                Debug.LogError($"[ClaudeUnityBridge] Error cleaning responses: {ex}");
            }
        }

        [MenuItem("Tools/Claude Code Bridge/Show Status")]
        public static void ShowStatus()
        {
            var status = ClaudeUnityBridge.GetBridgeStatus();
            Debug.Log($"[ClaudeUnityBridge] Status:\n" +
                     $"Initialized: {status.isInitialized}\n" +
                     $"Play Mode State: {status.playModeState}\n" +
                     $"File Watcher Active: {status.isWatcherActive}\n" +
                     $"Commands Path: {COMMANDS_PATH}\n" +
                     $"Responses Path: {RESPONSES_PATH}\n" +
                     $"Registered Handlers: {status.handlerNames}\n" +
                     $"Processed Commands: {status.processedCount}");
        }

        [MenuItem("Tools/Claude Code Bridge/Reset Bridge")]
        public static void ResetBridge()
        {
            Debug.Log("[ClaudeUnityBridge] Manual reset requested");
            ClaudeUnityBridge.ResetBridge();
            Debug.Log("[ClaudeUnityBridge] Reset complete - bridge reinitialized");
        }

        #endregion
    }
}

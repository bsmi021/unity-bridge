using System;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Centralized logging for Claude Unity Bridge with configurable log levels.
    ///
    /// Log levels (in order of verbosity):
    /// - Off: No logging
    /// - Error: Only errors
    /// - Warning: Errors and warnings
    /// - Info: Errors, warnings, and informational messages
    /// - Debug: All messages including debug details
    ///
    /// The log level can be changed via:
    /// - Tools > Claude Code Bridge > Set Log Level menu
    /// - Programmatically via BridgeLogger.LogLevel property
    /// - EditorPrefs persists the setting between sessions
    /// </summary>
    public static class BridgeLogger
    {
        private const string LOG_PREFIX = "[ClaudeUnityBridge]";
        private const string PREFS_KEY = "ClaudeUnityBridge_LogLevel";

        /// <summary>
        /// Available logging levels in order of increasing verbosity.
        /// </summary>
        public enum Level
        {
            Off = 0,
            Error = 1,
            Warning = 2,
            Info = 3,
            Debug = 4
        }

        private static Level _logLevel = Level.Warning; // Default to Warning
        private static bool _initialized = false;

        /// <summary>
        /// Current log level. Changes are persisted to EditorPrefs.
        /// </summary>
        public static Level LogLevel
        {
            get
            {
                EnsureInitialized();
                return _logLevel;
            }
            set
            {
                _logLevel = value;
                EditorPrefs.SetInt(PREFS_KEY, (int)value);
            }
        }

        /// <summary>
        /// Initialize logger from EditorPrefs.
        /// </summary>
        private static void EnsureInitialized()
        {
            if (_initialized) return;

            if (EditorPrefs.HasKey(PREFS_KEY))
            {
                _logLevel = (Level)EditorPrefs.GetInt(PREFS_KEY, (int)Level.Warning);
            }
            _initialized = true;
        }

        /// <summary>
        /// Log a debug message (most verbose level).
        /// Use for detailed operational information.
        /// </summary>
        public static void LogDebug(string message)
        {
            if (LogLevel >= Level.Debug)
            {
                Debug.Log($"{LOG_PREFIX} {message}");
            }
        }

        /// <summary>
        /// Log an info message.
        /// Use for significant operational events.
        /// </summary>
        public static void LogInfo(string message)
        {
            if (LogLevel >= Level.Info)
            {
                Debug.Log($"{LOG_PREFIX} {message}");
            }
        }

        /// <summary>
        /// Log a warning message.
        /// Use for unexpected but recoverable situations.
        /// </summary>
        public static void LogWarning(string message)
        {
            if (LogLevel >= Level.Warning)
            {
                Debug.LogWarning($"{LOG_PREFIX} {message}");
            }
        }

        /// <summary>
        /// Log an error message.
        /// Use for failures and exceptions.
        /// </summary>
        public static void LogError(string message)
        {
            if (LogLevel >= Level.Error)
            {
                Debug.LogError($"{LOG_PREFIX} {message}");
            }
        }

        /// <summary>
        /// Log an exception with error level.
        /// </summary>
        public static void LogException(string context, Exception ex)
        {
            if (LogLevel >= Level.Error)
            {
                Debug.LogError($"{LOG_PREFIX} {context}: {ex}");
            }
        }

        #region Menu Items for Log Level Configuration

        [MenuItem("Tools/Claude Code Bridge/Log Level/Off", false, 500)]
        private static void SetLogLevelOff() => SetLevelWithFeedback(Level.Off);

        [MenuItem("Tools/Claude Code Bridge/Log Level/Error", false, 501)]
        private static void SetLogLevelError() => SetLevelWithFeedback(Level.Error);

        [MenuItem("Tools/Claude Code Bridge/Log Level/Warning (Default)", false, 502)]
        private static void SetLogLevelWarning() => SetLevelWithFeedback(Level.Warning);

        [MenuItem("Tools/Claude Code Bridge/Log Level/Info", false, 503)]
        private static void SetLogLevelInfo() => SetLevelWithFeedback(Level.Info);

        [MenuItem("Tools/Claude Code Bridge/Log Level/Debug (Verbose)", false, 504)]
        private static void SetLogLevelDebug() => SetLevelWithFeedback(Level.Debug);

        private static void SetLevelWithFeedback(Level level)
        {
            LogLevel = level;
            // Always show this feedback regardless of log level
            Debug.Log($"{LOG_PREFIX} Log level set to: {level}");
        }

        // Validation methods to show checkmarks in menu
        [MenuItem("Tools/Claude Code Bridge/Log Level/Off", true)]
        private static bool ValidateLogLevelOff() { Menu.SetChecked("Tools/Claude Code Bridge/Log Level/Off", LogLevel == Level.Off); return true; }

        [MenuItem("Tools/Claude Code Bridge/Log Level/Error", true)]
        private static bool ValidateLogLevelError() { Menu.SetChecked("Tools/Claude Code Bridge/Log Level/Error", LogLevel == Level.Error); return true; }

        [MenuItem("Tools/Claude Code Bridge/Log Level/Warning (Default)", true)]
        private static bool ValidateLogLevelWarning() { Menu.SetChecked("Tools/Claude Code Bridge/Log Level/Warning (Default)", LogLevel == Level.Warning); return true; }

        [MenuItem("Tools/Claude Code Bridge/Log Level/Info", true)]
        private static bool ValidateLogLevelInfo() { Menu.SetChecked("Tools/Claude Code Bridge/Log Level/Info", LogLevel == Level.Info); return true; }

        [MenuItem("Tools/Claude Code Bridge/Log Level/Debug (Verbose)", true)]
        private static bool ValidateLogLevelDebug() { Menu.SetChecked("Tools/Claude Code Bridge/Log Level/Debug (Verbose)", LogLevel == Level.Debug); return true; }

        #endregion
    }
}

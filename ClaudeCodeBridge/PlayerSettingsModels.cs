using System;
using System.Collections.Generic;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    #region Player Settings Operation Command

    /// <summary>
    /// Parameters for the player-settings-operation command.
    /// Supports get, set, defines-list, defines-add, defines-remove operations.
    /// </summary>
    [Serializable]
    public class PlayerSettingsOperationParams
    {
        public string operation; // "get", "set", "defines-list", "defines-add", "defines-remove"
        public string key;
        public string value;
        public string symbol;
        public string platform; // NamedBuildTarget name (default: active)
    }

    /// <summary>
    /// Result data for the player-settings-operation command.
    /// </summary>
    [Serializable]
    public class PlayerSettingsOperationResult
    {
        public string operation;
        public string key;
        public string value;
        public string previousValue;
        public string newValue;
        public string platform;
        public string symbol;
        public List<string> defines = new List<string>();
        public bool triggeredRecompilation;
        public bool domainReloadPending;
        public int totalCount;
        public PlayerSettingsData settings;
        public bool success;
        public string message;
    }

    /// <summary>
    /// Snapshot of commonly-automated PlayerSettings fields.
    /// </summary>
    [Serializable]
    public class PlayerSettingsData
    {
        public string companyName;
        public string productName;
        public string bundleVersion;
        public string applicationIdentifier;
        public bool defaultIsFullScreen;
        public bool runInBackground;
        public string apiCompatibilityLevel;
        public string scriptingBackend;
        public string targetArchitecture;
    }

    #endregion
}

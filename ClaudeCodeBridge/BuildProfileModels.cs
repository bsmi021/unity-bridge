using System;
using System.Collections.Generic;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    #region Build Profile Operation Command

    /// <summary>
    /// Parameters for the build-profile-operation command.
    /// Supports list, get-active, set-active, get-info operations.
    /// </summary>
    [Serializable]
    public class BuildProfileOperationParams
    {
        public string operation; // "list", "get-active", "set-active", "get-info"
        public string profilePath; // Asset path to build profile
    }

    /// <summary>
    /// Result data for the build-profile-operation command.
    /// </summary>
    [Serializable]
    public class BuildProfileOperationResult
    {
        public string operation;
        public List<BuildProfileInfo> profiles = new List<BuildProfileInfo>();
        public BuildProfileInfo profile; // Single profile result
        public int totalCount;
        public bool success;
        public string message;
    }

    /// <summary>
    /// Information about a Unity 6 Build Profile.
    /// </summary>
    [Serializable]
    public class BuildProfileInfo
    {
        public string assetPath;
        public string name;
        public string platform;
        public bool isActive;
        public List<string> scenes = new List<string>();
        public string scriptingDefines;
        public string buildTarget;
        public string subtarget;
        public string il2CppCodeGeneration;
        public string managedStrippingLevel;
    }

    #endregion
}

using System;
using System.Collections.Generic;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    #region Build Profile Operation Command

    /// <summary>
    /// Parameters for the build-profile-operation command.
    /// Supports list, get-active, set-active, get-info, scene/define mutation, and build operations.
    /// </summary>
    [Serializable]
    public class BuildProfileOperationParams
    {
        public string operation;
        public string profilePath; // Asset path to build profile
        public string profileName;
        public string platformId;
        public string outputPath;
        public List<string> scenes;
        public List<string> disabledScenes;
        public List<string> scriptingDefines;
        public bool development;
        public bool autoRunPlayer;
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
        public string profilePath;
        public string outputPath;
        public List<BuildProfileSceneInfo> scenes = new List<BuildProfileSceneInfo>();
        public List<string> scriptingDefines = new List<string>();
        public int totalCount;
        public bool success;
        public string message;
        public BuildReportSummary summary;
        public List<BuildReportStep> buildSteps = new List<BuildReportStep>();
        public List<BuildReportAsset> largestAssets = new List<BuildReportAsset>();
        public int errorCount;
        public int warningCount;
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
        public List<BuildProfileSceneInfo> sceneEntries = new List<BuildProfileSceneInfo>();
        public string scriptingDefines;
        public List<string> scriptingDefineEntries = new List<string>();
        public string buildTarget;
        public string subtarget;
        public string il2CppCodeGeneration;
        public string managedStrippingLevel;
    }

    [Serializable]
    public class BuildProfileSceneInfo
    {
        public string path;
        public bool enabled;
    }

    #endregion
}

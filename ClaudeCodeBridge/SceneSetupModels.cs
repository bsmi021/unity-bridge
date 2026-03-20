using System;
using System.Collections.Generic;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Parameters for the scene-setup-operation command.
    /// Supports: save, restore, list, play-start, cross-refs,
    /// list-loaded, preview-create, preview-close.
    /// </summary>
    [Serializable]
    public class SceneSetupParams
    {
        public string operation;
        public string setupName;
        public string scenePath;
        public bool clear;
        public int handle = -1;
    }

    /// <summary>
    /// Scene info within a setup.
    /// </summary>
    [Serializable]
    public class SceneSetupEntry
    {
        public string path;
        public bool isLoaded;
        public bool isActive;
        public bool isSubScene;
    }

    /// <summary>
    /// Result data for setup save/restore operations.
    /// </summary>
    [Serializable]
    public class SceneSetupResult
    {
        public string operation;
        public string setupName;
        public string setupPath;
        public List<SceneSetupEntry> scenes = new List<SceneSetupEntry>();
        public int sceneCount;
        public bool success;
        public string message;
    }

    /// <summary>
    /// Stored setup file format (serialized to JSON on disk).
    /// </summary>
    [Serializable]
    public class SceneSetupFile
    {
        public string name;
        public string createdAt;
        public string updatedAt;
        public List<SceneSetupEntry> scenes = new List<SceneSetupEntry>();
    }

    /// <summary>
    /// Summary info for setup listing.
    /// </summary>
    [Serializable]
    public class SceneSetupSummary
    {
        public string name;
        public int sceneCount;
        public string createdAt;
        public string activeScene;
    }

    /// <summary>
    /// Result data for setup list operation.
    /// </summary>
    [Serializable]
    public class SceneSetupListResult
    {
        public string operation;
        public List<SceneSetupSummary> setups = new List<SceneSetupSummary>();
        public int setupCount;
        public bool success;
        public string message;
    }

    /// <summary>
    /// Result data for play-start operation.
    /// </summary>
    [Serializable]
    public class PlayStartResult
    {
        public string operation;
        public string playModeStartScene;
        public bool isSet;
        public bool success;
        public string message;
    }

    /// <summary>
    /// Cross-reference info for a single scene.
    /// </summary>
    [Serializable]
    public class CrossRefInfo
    {
        public string scenePath;
        public bool hasCrossRefs;
    }

    /// <summary>
    /// Result data for cross-refs operation.
    /// </summary>
    [Serializable]
    public class CrossRefsResult
    {
        public string operation;
        public List<string> loadedScenes = new List<string>();
        public List<CrossRefInfo> crossReferences = new List<CrossRefInfo>();
        public int totalWithCrossRefs;
        public bool success;
        public string message;
    }

    /// <summary>
    /// Loaded scene info for list-loaded operation.
    /// </summary>
    [Serializable]
    public class LoadedSceneInfo
    {
        public string name;
        public string path;
        public int buildIndex;
        public bool isLoaded;
        public bool isActive;
        public bool isDirty;
        public int rootCount;
    }

    /// <summary>
    /// Result data for list-loaded operation.
    /// </summary>
    [Serializable]
    public class ListLoadedResult
    {
        public string operation;
        public List<LoadedSceneInfo> scenes = new List<LoadedSceneInfo>();
        public int loadedCount;
        public bool success;
        public string message;
    }

    /// <summary>
    /// Result data for preview-create operation.
    /// </summary>
    [Serializable]
    public class PreviewCreateResult
    {
        public string operation;
        public int handle;
        public string sceneName;
        public bool success;
        public string message;
    }

    /// <summary>
    /// Result data for preview-close operation.
    /// </summary>
    [Serializable]
    public class PreviewCloseResult
    {
        public string operation;
        public int handle;
        public bool success;
        public string message;
    }

    /// <summary>
    /// Result for restore operation when scenes are missing.
    /// </summary>
    [Serializable]
    public class SceneSetupRestoreError
    {
        public string operation;
        public string setupName;
        public List<string> missingScenes = new List<string>();
        public bool success;
        public string message;
    }
}

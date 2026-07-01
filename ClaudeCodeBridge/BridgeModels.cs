using System;
using System.Collections.Generic;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Base class for all commands sent from Claude Code to Unity.
    /// Commands are serialized as JSON files in .claude/unity/commands/
    /// </summary>
    [Serializable]
    public class BridgeCommand
    {
        public string commandId;
        public string commandType;
        public string timestamp;
        public string parametersJson;
    }

    /// <summary>
    /// Base class for all responses sent from Unity to Claude Code.
    /// Responses are serialized as JSON files in .claude/unity/responses/
    /// </summary>
    [Serializable]
    public class BridgeResponse
    {
        public string commandId;
        public string commandType;
        public string status; // "success", "error", "running"
        public string timestamp;
        public string dataJson;
        public string errorMessage;

        public static BridgeResponse Success(string commandId, string commandType, string dataJson = null)
        {
            return new BridgeResponse
            {
                commandId = commandId,
                commandType = commandType,
                status = "success",
                timestamp = DateTime.UtcNow.ToString("o"),
                dataJson = dataJson
            };
        }

        public static BridgeResponse Error(string commandId, string commandType, string errorMessage)
        {
            return new BridgeResponse
            {
                commandId = commandId,
                commandType = commandType,
                status = "error",
                timestamp = DateTime.UtcNow.ToString("o"),
                errorMessage = errorMessage
            };
        }

        public static BridgeResponse Running(string commandId, string commandType, string dataJson = null)
        {
            return new BridgeResponse
            {
                commandId = commandId,
                commandType = commandType,
                status = "running",
                timestamp = DateTime.UtcNow.ToString("o"),
                dataJson = dataJson
            };
        }
    }

    /// <summary>
    /// Parameters for the run-tests command.
    /// </summary>
    [Serializable]
    public class RunTestsParams
    {
        public string testFilter; // Optional filter like "CombatControllerTests" or null for all tests
        public string testPlatform = "EditMode"; // "EditMode" or "PlayMode"
        public string[] testNames; // Full test names to execute
        public string[] groupNames; // Regex-style fixture/namespace groups to execute
        public string[] categoryNames; // NUnit categories to include
        public string[] assemblyNames; // Test assembly names without .dll
    }

    /// <summary>
    /// Parameters for the cancel-tests command.
    /// </summary>
    [Serializable]
    public class CancelTestsParams
    {
        public string targetCommandId; // Optional originating run-tests bridge command id
    }

    /// <summary>
    /// Result data for the cancel-tests command.
    /// </summary>
    [Serializable]
    public class CancelTestsResult
    {
        public string targetCommandId;
        public string runGuid;
        public bool activeRun;
        public bool cancelRequested;
        public string message;
    }

    /// <summary>
    /// Result data for the run-tests command.
    /// </summary>
    [Serializable]
    public class RunTestsResult
    {
        public int total;
        public int passed;
        public int failed;
        public int skipped;
        public int inconclusive;
        public double durationSeconds;
        public string resultState;       // e.g. "Passed", "Failed"
        public string testSuite;         // root fixture full name
        public List<TestFailureInfo> failures = new List<TestFailureInfo>();
        public List<TestCaseInfo> testCases = new List<TestCaseInfo>();
    }

    [Serializable]
    public class TestFailureInfo
    {
        public string testName;
        public string errorMessage;
        public string stackTrace;
    }

    /// <summary>
    /// Per-test summary for the NUnit-style result breakdown.
    /// </summary>
    [Serializable]
    public class TestCaseInfo
    {
        public string fullName;
        public string status;            // Passed / Failed / Skipped / Inconclusive
        public double durationSeconds;
        public string assembly;
        public string categories;        // semicolon-separated
    }

    #region Query Hierarchy Command

    /// <summary>
    /// Parameters for the query-hierarchy command.
    /// Retrieves GameObject hierarchy information from the active scene.
    /// </summary>
    [Serializable]
    public class QueryHierarchyParams
    {
        public string gameObjectName; // Optional - filter by GameObject name (partial match)
        public bool includeInactive = false; // Include inactive GameObjects
        public int maxDepth = -1; // Max hierarchy depth (-1 = unlimited)
        public int depth = -1; // Alias for maxDepth (CLI sends "depth")
        public string rootPath; // Optional - start from this GameObject path

        /// <summary>Resolve effective max depth (CLI sends "depth", MCP sends "maxDepth").</summary>
        public int EffectiveMaxDepth => depth >= 0 ? depth : maxDepth;
    }

    /// <summary>
    /// Result data for the query-hierarchy command.
    /// </summary>
    [Serializable]
    public class QueryHierarchyResult
    {
        public List<GameObjectInfo> gameObjects = new List<GameObjectInfo>();
        public int totalCount;
    }

    [Serializable]
    public class GameObjectInfo
    {
        public string name;
        public string path; // Full hierarchy path
        public bool isActive;
        public string tag;
        public int layer;
        public List<string> components = new List<string>(); // Component type names
        public List<GameObjectInfo> children = new List<GameObjectInfo>();
    }

    #endregion

    #region Get Component Data Command

    /// <summary>
    /// Parameters for the get-component-data command.
    /// Reads serialized field values from a component.
    /// </summary>
    [Serializable]
    public class GetComponentDataParams
    {
        public string gameObjectPath; // Full hierarchy path (e.g., "Player/Camera")
        public string componentType; // Component type name (e.g., "Transform", "BWS.CharacterStats")
        public List<string> fieldNames = new List<string>(); // Optional - specific fields to read (empty = all public fields)
    }

    /// <summary>
    /// Result data for the get-component-data command.
    /// </summary>
    [Serializable]
    public class GetComponentDataResult
    {
        public string gameObjectPath;
        public string componentType;
        public List<ComponentFieldInfo> fields = new List<ComponentFieldInfo>();
    }

    [Serializable]
    public class ComponentFieldInfo
    {
        public string name;
        public string type;
        public string value; // JSON representation of value
    }

    #endregion

    #region Set Component Data Command

    /// <summary>
    /// Parameters for the set-component-data command.
    /// Modifies serialized field values on a component.
    /// </summary>
    [Serializable]
    public class SetComponentDataParams
    {
        public string gameObjectPath; // Full hierarchy path
        public string componentType; // Component type name
        public List<FieldUpdate> fieldUpdates = new List<FieldUpdate>(); // Fields to update
    }

    [Serializable]
    public class FieldUpdate
    {
        public string fieldName;
        public string valueJson; // JSON representation of new value
    }

    /// <summary>
    /// Result data for the set-component-data command.
    /// </summary>
    [Serializable]
    public class SetComponentDataResult
    {
        public string gameObjectPath;
        public string componentType;
        public int fieldsUpdated;
        public List<string> updatedFields = new List<string>();
    }

    #endregion

    #region Add Component Command

    /// <summary>
    /// Parameters for the add-component command.
    /// Adds a component to a GameObject.
    /// </summary>
    [Serializable]
    public class AddComponentParams
    {
        public string gameObjectPath; // Full hierarchy path
        public string componentType; // Full component type name (e.g., "UnityEngine.Rigidbody", "BWS.CharacterStats")
    }

    /// <summary>
    /// Result data for the add-component command.
    /// </summary>
    [Serializable]
    public class AddComponentResult
    {
        public string gameObjectPath;
        public string componentType;
        public bool success;
        public string message;
    }

    #endregion

    #region Validate Prefab Command

    /// <summary>
    /// Parameters for the validate-prefab command.
    /// Validates a prefab's configuration and dependencies.
    /// </summary>
    [Serializable]
    public class ValidatePrefabParams
    {
        public string prefabPath; // Asset path (e.g., "Assets/Prefabs/Player.prefab")
        public bool checkMissingReferences = true;
        public bool checkMissingComponents = true;
    }

    /// <summary>
    /// Result data for the validate-prefab command.
    /// </summary>
    [Serializable]
    public class ValidatePrefabResult
    {
        public string prefabPath;
        public bool isValid;
        public List<ValidationIssue> issues = new List<ValidationIssue>();
    }

    [Serializable]
    public class ValidationIssue
    {
        public string severity; // "error", "warning", "info"
        public string message;
        public string objectPath; // Path within prefab hierarchy
    }

    #endregion

    #region Profiler Sample Command

    /// <summary>
    /// Parameters for the profiler-sample command.
    /// Captures a performance snapshot.
    /// </summary>
    [Serializable]
    public class ProfilerSampleParams
    {
        public bool includeMemory = true;
        public bool includeRendering = true;
        public bool includePhysics = false;
    }

    /// <summary>
    /// Result data for the profiler-sample command.
    /// </summary>
    [Serializable]
    public class ProfilerSampleResult
    {
        public long totalMemoryMB;
        public long monoMemoryMB;
        public long graphicsMemoryMB;
        public int drawCalls;
        public int triangles;
        public int vertices;
        public float lastFrameTime;
        public List<string> topAllocators = new List<string>();
    }

    #endregion

    #region Asset Operation Command

    /// <summary>
    /// Parameters for the asset-operation command.
    /// Performs various operations on Unity assets via AssetDatabase.
    /// </summary>
    [Serializable]
    public class AssetOperationParams
    {
        public string operation; // "find", "get-dependencies", "import", "refresh", "get-info"
        public string assetPath; // e.g., "Assets/Prefabs/"
        public string searchPattern; // e.g., "Enemy*" for find operation
        public string assetType; // e.g., "Prefab", "Material", "ScriptableObject"
        public bool recursive = true; // For find operation
    }

    /// <summary>
    /// Result data for the asset-operation command.
    /// </summary>
    [Serializable]
    public class AssetOperationResult
    {
        public string operation;
        public List<AssetInfo> assets = new List<AssetInfo>();
        public List<string> dependencies = new List<string>();
        public bool success;
        public string message;
    }

    /// <summary>
    /// Information about a Unity asset.
    /// </summary>
    [Serializable]
    public class AssetInfo
    {
        public string path;
        public string guid;
        public string type;
        public long fileSize;
    }

    #endregion

    #region Scene Operation Command

    /// <summary>
    /// Parameters for the scene-operation command.
    /// Performs various operations on Unity scenes.
    /// </summary>
    [Serializable]
    public class SceneOperationParams
    {
        public string operation; // "load", "save", "create", "list", "unload", "set-active"
        public string scenePath; // e.g., "Assets/Scenes/GameplayScene.unity"
        public bool saveCurrentScene = true; // Save before switching
        public string mode; // "single" (default), "additive", "additive-without-loading"
        public bool removeScene = true; // For "unload" operation
        public string gameObjectPath; // For "move-object" operation
    }

    /// <summary>
    /// Result data for the scene-operation command.
    /// </summary>
    [Serializable]
    public class SceneOperationResult
    {
        public string operation;
        public string currentScenePath;
        public List<string> scenePaths = new List<string>(); // For "list" operation
        public bool success;
        public string message;
    }

    #endregion

    #region Capture Screenshot Command

    /// <summary>
    /// Parameters for the capture-screenshot command.
    /// Captures screenshots from scene view or game view cameras.
    /// </summary>
    [Serializable]
    public class CaptureScreenshotParams
    {
        public string cameraPath; // GameObject path to camera, or "SceneView" for scene camera
        public int width = 1920;
        public int height = 1080;
        public string outputPath; // e.g., "Screenshots/test_capture.png"
        public bool captureUI = false; // Include UI in capture
    }

    /// <summary>
    /// Result data for the capture-screenshot command.
    /// </summary>
    [Serializable]
    public class CaptureScreenshotResult
    {
        public string outputPath;
        public int width;
        public int height;
        public long fileSizeBytes;
        public bool success;
        public string message;
    }

    #endregion

    #region PlayMode Control Command

    /// <summary>
    /// Parameters for the playmode-control command.
    /// Controls Unity Editor play mode state.
    /// </summary>
    [Serializable]
    public class PlayModeControlParams
    {
        public string operation; // "play", "pause", "stop", "step", "status"
        public string action; // Legacy alias for operation
        public string targetScene; // Optional: load scene before playing
    }

    /// <summary>
    /// Result data for the playmode-control command.
    /// </summary>
    [Serializable]
    public class PlayModeControlResult
    {
        public string operation;
        public string playModeState; // "Stopped", "Playing", "Paused"
        public bool isPaused;
        public string currentScene;
        public bool success;
        public string message;
    }

    #endregion

    #region Build Operation Command

    /// <summary>
    /// Parameters for the build-operation command.
    /// Triggers build operations or retrieves build settings.
    /// </summary>
    [Serializable]
    public class BuildOperationParams
    {
        public string operation; // "build", "get-settings", "validate", "get-target", "switch-platform", "list-platforms"
        public string target; // "StandaloneWindows64", "Android", etc.
        public string outputPath; // Build output path
        public bool development = false; // Development build flag
        public bool autoRunPlayer = false;
        public bool connectProfiler = false;
        public bool allowDebugging = false;
        public bool cleanBuildCache = false;
        public bool detailedBuildReport = false;
        public bool buildScriptsOnly = false;
        public string compress; // "lz4", "lz4hc", or null
        public string scenes; // Comma-separated scene paths
        public string subtarget; // "Server", "Player"
    }

    [Serializable]
    public class PlatformListResult
    {
        public string operation;
        public string activePlatform;
        public bool success;
        public string message;
        public List<PlatformInfo> platforms = new List<PlatformInfo>();
    }

    [Serializable]
    public class PlatformInfo
    {
        public string name;
        public bool isSupported;
        public bool isActive;
    }

    /// <summary>
    /// Result data for the build-operation command.
    /// </summary>
    [Serializable]
    public class BuildOperationResult
    {
        public string operation;
        public string buildTarget;
        public string outputPath;
        public List<string> scenes = new List<string>();
        public List<string> errors = new List<string>();
        public List<string> warnings = new List<string>();
        public bool success;
        public string message;

        // Structured BuildReport fields (Phase 7a-2) — exposed so callers
        // don't need to re-parse the raw Editor.log. Populated on completed
        // builds; zero/empty for validate / in-progress responses.
        public BuildReportSummary summary;
        public List<BuildReportStep> buildSteps = new List<BuildReportStep>();
        public List<BuildReportAsset> largestAssets = new List<BuildReportAsset>();
        public int errorCount;
        public int warningCount;
    }

    [Serializable]
    public class BuildReportSummary
    {
        public string result;                // Succeeded / Failed / Cancelled / Unknown
        public string platform;
        public string platformGroup;
        public long totalSizeBytes;
        public double totalSizeMb;
        public double totalTimeSeconds;
        public string buildStartedAt;
        public string buildEndedAt;
        public string outputPath;
        public string buildGuid;
    }

    [Serializable]
    public class BuildReportStep
    {
        public string name;
        public double durationSeconds;
        public int depth;
        public int messageCount;
    }

    [Serializable]
    public class BuildReportAsset
    {
        public string assetPath;
        public long sizeBytes;
        public double sizeMb;
        public string kind;      // source asset / scene / script / shader / etc.
    }

    #endregion

    // Models below have been moved to BridgeModelsPhase3.cs:
    // - ReadConsoleParams, ReadConsoleResult, ConsoleEntry
    // - PrefabOperationParams, PrefabOperationResult
    // - AnimatorOperationParams, TransitionCondition, AnimatorOperationResult
    // - AnimatorLayerInfo, AnimatorStateInfo, AnimatorParameterInfo, AnimatorTransitionInfo
    // - MaterialOperationParams, MaterialProperty, MaterialOperationResult
    // - GameObjectOperationParams, GameObjectOperationResult
    // - BridgeStatusParams, BridgeStatusResult

    /// <summary>
    /// Interface for command handlers.
    /// Each command type implements this to process commands.
    /// </summary>
    public interface ICommandHandler
    {
        /// <summary>
        /// The command type this handler processes (e.g., "run-tests").
        /// </summary>
        string CommandType { get; }

        /// <summary>
        /// Execute the command and return a response.
        /// This runs on the main Unity thread.
        /// </summary>
        BridgeResponse Execute(BridgeCommand command);
    }
}

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
        public double durationSeconds;
        public List<TestFailureInfo> failures = new List<TestFailureInfo>();
    }

    [Serializable]
    public class TestFailureInfo
    {
        public string testName;
        public string errorMessage;
        public string stackTrace;
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
        public string operation; // "load", "save", "create", "list"
        public string scenePath; // e.g., "Assets/Scenes/GameplayScene.unity"
        public bool saveCurrentScene = true; // Save before switching
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
        public string operation; // "build", "get-settings", "validate", "get-target"
        public string target; // "StandaloneWindows64", "Android", etc.
        public string outputPath; // Build output path
        public bool development = false; // Development build flag
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
    }

    #endregion

    #region Material Operation Command

    /// <summary>
    /// Parameters for the material-operation command.
    /// Manages material creation, modification, and property inspection.
    /// </summary>
    [Serializable]
    public class MaterialOperationParams
    {
        public string operation; // "create", "modify", "get-properties", "set-shader"
        public string materialPath; // e.g., "Assets/Materials/CharacterMat.mat"
        public string shader; // e.g., "Universal Render Pipeline/Lit"
        public List<MaterialProperty> properties = new List<MaterialProperty>();
    }

    /// <summary>
    /// Represents a material property with its name, type, and value.
    /// </summary>
    [Serializable]
    public class MaterialProperty
    {
        public string name; // e.g., "_Color", "_MainTex"
        public string type; // "Color", "Float", "Texture", "Vector"
        public string valueJson; // JSON representation of value
    }

    /// <summary>
    /// Result data for the material-operation command.
    /// </summary>
    [Serializable]
    public class MaterialOperationResult
    {
        public string operation;
        public string materialPath;
        public string shaderName;
        public List<MaterialProperty> properties = new List<MaterialProperty>();
        public bool success;
        public string message;
    }

    #endregion

    #region Read Console Command

    /// <summary>
    /// Parameters for the read-console command.
    /// Reads Unity Console logs (errors, warnings, messages).
    /// </summary>
    [Serializable]
    public class ReadConsoleParams
    {
        public List<string> logTypes = new List<string>(); // ["Error", "Warning", "Log"] - empty = all
        public int maxEntries = 100; // Max number of entries to return
        public bool clearAfterRead = false; // Clear console after reading
        public bool includeStackTrace = true; // Include stack trace in output (default: true)
        public int maxStackTraceLines = 5; // Max lines of stack trace to include (0 = unlimited, -1 = none)
        public int maxMessageLength = 500; // Max characters for message (0 = unlimited)
    }

    /// <summary>
    /// Result data for the read-console command.
    /// </summary>
    [Serializable]
    public class ReadConsoleResult
    {
        public List<ConsoleEntry> entries = new List<ConsoleEntry>();
        public int totalCount;
    }

    /// <summary>
    /// Represents a single Unity Console log entry.
    /// </summary>
    [Serializable]
    public class ConsoleEntry
    {
        public string logType; // "Error", "Warning", "Log"
        public string message;
        public string stackTrace;
        public string timestamp;
    }

    #endregion

    #region Prefab Operation Command

    /// <summary>
    /// Parameters for the prefab-operation command.
    /// Performs various prefab operations (create, instantiate, apply, revert, get-info).
    /// </summary>
    [Serializable]
    public class PrefabOperationParams
    {
        public string operation; // "create", "instantiate", "apply", "revert", "get-info"
        public string prefabPath; // e.g., "Assets/Prefabs/Enemy.prefab"
        public string gameObjectPath; // Source GameObject for create, or target for instantiate
        public bool applyToAll = false; // For apply operation
    }

    /// <summary>
    /// Result data for the prefab-operation command.
    /// </summary>
    [Serializable]
    public class PrefabOperationResult
    {
        public string operation;
        public string prefabPath;
        public string gameObjectPath;
        public bool isPrefabInstance;
        public bool hasModifications;
        public List<string> modifications = new List<string>();
        public bool success;
        public string message;
    }

    #endregion

    #region Animator Operation Command

    /// <summary>
    /// Parameters for the animator-operation command.
    /// Performs comprehensive Animator Controller operations.
    /// </summary>
    [Serializable]
    public class AnimatorOperationParams
    {
        public string operation; // "create-controller", "add-layer", "add-state", "add-transition", etc.
        public string controllerPath; // Path to Animator Controller asset
        public string layerName = "Base Layer"; // Target layer name
        public int layerIndex = 0; // Alternative to layerName
        public float weight = 1.0f; // Layer weight
        public string blendingMode = "Override"; // "Override" or "Additive"
        public string stateName; // State name
        public string sourceState; // Source state for transitions
        public string destinationState; // Destination state for transitions
        public string animationClipPath; // Path to animation clip asset
        public float speed = 1.0f; // State playback speed multiplier
        public string parameterName; // Parameter name
        public string parameterType; // "Float", "Int", "Bool", "Trigger"
        public string defaultValue; // Default parameter value (JSON)
        public List<TransitionCondition> conditions = new List<TransitionCondition>(); // Transition conditions
        public float duration = 0.25f; // Transition duration
        public bool hasExitTime = true; // Whether transition has exit time
        public float exitTime = 0.75f; // Normalized exit time (0.0-1.0)
        public bool iKPass = false; // IK pass flag for layer
        public string avatarMaskPath; // Path to AvatarMask asset
    }

    /// <summary>
    /// Represents a transition condition for animator transitions.
    /// </summary>
    [Serializable]
    public class TransitionCondition
    {
        public string parameter; // Parameter name
        public string mode; // "If", "IfNot", "Greater", "Less", "Equals", "NotEqual"
        public float threshold; // Threshold value for comparison
    }

    /// <summary>
    /// Result data for the animator-operation command.
    /// </summary>
    [Serializable]
    public class AnimatorOperationResult
    {
        public string operation;
        public string controllerPath;
        public List<AnimatorLayerInfo> layers = new List<AnimatorLayerInfo>();
        public List<AnimatorStateInfo> states = new List<AnimatorStateInfo>();
        public List<AnimatorParameterInfo> parameters = new List<AnimatorParameterInfo>();
        public List<AnimatorTransitionInfo> transitions = new List<AnimatorTransitionInfo>();
        public bool success;
        public string message;
    }

    /// <summary>
    /// Information about an animator layer.
    /// </summary>
    [Serializable]
    public class AnimatorLayerInfo
    {
        public string name;
        public float weight;
        public string blendingMode;
        public int stateCount;
        public bool iKPass;
        public string avatarMask;
    }

    /// <summary>
    /// Information about an animator state.
    /// </summary>
    [Serializable]
    public class AnimatorStateInfo
    {
        public string name;
        public string layerName;
        public string motionPath;
        public float speed;
        public bool isDefaultState;
        public string tag;
    }

    /// <summary>
    /// Information about an animator parameter.
    /// </summary>
    [Serializable]
    public class AnimatorParameterInfo
    {
        public string name;
        public string type; // "Float", "Int", "Bool", "Trigger"
        public string defaultValue;
    }

    /// <summary>
    /// Information about an animator transition.
    /// </summary>
    [Serializable]
    public class AnimatorTransitionInfo
    {
        public string sourceState;
        public string destinationState;
        public float duration;
        public bool hasExitTime;
        public float exitTime;
        public int conditionCount;
        public List<TransitionCondition> conditions = new List<TransitionCondition>();
    }

    #endregion

    #region GameObject Operation Command

    /// <summary>
    /// Parameters for the gameobject-operation command.
    /// Performs various GameObject operations (create, delete, rename).
    /// </summary>
    [Serializable]
    public class GameObjectOperationParams
    {
        public string operation; // "create", "delete", "rename"
        public string gameObjectName; // Name for new GameObject (create operation)
        public string gameObjectPath; // Full hierarchy path (delete/rename operations)
        public string parentPath; // Parent path for create operation
        public string newName; // New name for rename operation
    }

    /// <summary>
    /// Result data for the gameobject-operation command.
    /// </summary>
    [Serializable]
    public class GameObjectOperationResult
    {
        public string operation;
        public string gameObjectPath;
        public bool success;
        public string message;
    }

    #endregion

    #region Bridge Status Command

    /// <summary>
    /// Parameters for the bridge-status command.
    /// Reports bridge health and configuration.
    /// </summary>
    [Serializable]
    public class BridgeStatusParams
    {
        // No parameters needed - just reports status
    }

    /// <summary>
    /// Result data for the bridge-status command.
    /// </summary>
    [Serializable]
    public class BridgeStatusResult
    {
        public string unityVersion;
        public bool isInitialized;
        public List<string> registeredHandlers = new List<string>();
        public int commandsProcessed;
        public string commandsPath;
        public string responsesPath;
        public string currentScene;
        public string playModeState;
    }

    #endregion

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

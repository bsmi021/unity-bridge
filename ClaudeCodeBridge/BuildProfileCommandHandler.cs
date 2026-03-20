#if UNITY_6000_0_OR_NEWER
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Profile;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for Unity 6 Build Profile operations.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "list" - List all build profiles in the project
    /// 2. "get-active" - Get the currently active build profile
    /// 3. "set-active" - Set the active build profile by path
    /// 4. "get-info" - Get detailed info about a specific build profile
    ///
    /// Requires Unity 6 (UNITY_6000_0_OR_NEWER). Not available in earlier versions.
    /// </summary>
    public class BuildProfileCommandHandler : ICommandHandler
    {
        public string CommandType => "build-profile-operation";

        private static readonly HashSet<string> MUTATING_OPERATIONS
            = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "set-active" };

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                // Guard: reject commands while compiling
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, CommandType,
                        "Unity is compiling. Wait for compilation to finish before sending commands.");
                }

                var parameters = JsonUtility.FromJson<BuildProfileOperationParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new BuildProfileOperationParams();

                // Guard: reject mutating operations during play mode
                if (EditorApplication.isPlaying && IsMutatingOperation(parameters.operation))
                {
                    return BridgeResponse.Error(command.commandId, CommandType,
                        "Cannot perform mutating operations during play mode. Exit play mode first.");
                }

                BridgeLogger.LogDebug($"Executing build profile operation: {parameters.operation}");

                BuildProfileOperationResult result;

                switch (parameters.operation?.ToLower())
                {
                    case "list":
                        result = ExecuteList();
                        break;
                    case "get-active":
                        result = ExecuteGetActive();
                        break;
                    case "set-active":
                        result = ExecuteSetActive(parameters);
                        break;
                    case "get-info":
                        result = ExecuteGetInfo(parameters);
                        break;
                    default:
                        result = new BuildProfileOperationResult
                        {
                            operation = parameters.operation,
                            success = false,
                            message = $"Unknown operation: {parameters.operation}. " +
                                      "Supported: list, get-active, set-active, get-info"
                        };
                        break;
                }

                var resultJson = JsonUtility.ToJson(result);
                BridgeLogger.LogInfo(
                    $"Build profile operation completed: {parameters.operation}, success={result.success}");

                return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"BuildProfile error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private static bool IsMutatingOperation(string operation)
        {
            return !string.IsNullOrEmpty(operation) && MUTATING_OPERATIONS.Contains(operation);
        }

        /// <summary>
        /// List all build profiles in the project via AssetDatabase.
        /// </summary>
        private BuildProfileOperationResult ExecuteList()
        {
            var result = new BuildProfileOperationResult { operation = "list" };

            var active = BuildProfile.GetActiveBuildProfile();
            string activeAssetPath = active != null ? AssetDatabase.GetAssetPath(active) : null;

            string[] guids = AssetDatabase.FindAssets("t:BuildProfile");
            foreach (var guid in guids)
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                var profile = AssetDatabase.LoadAssetAtPath<BuildProfile>(path);
                if (profile == null) continue;

                var info = new BuildProfileInfo
                {
                    assetPath = path,
                    name = Path.GetFileNameWithoutExtension(path),
                    platform = profile.buildTarget.ToString(),
                    isActive = path == activeAssetPath,
                };
                result.profiles.Add(info);
            }

            result.totalCount = result.profiles.Count;
            result.success = true;
            result.message = $"Found {result.totalCount} build profiles";
            return result;
        }

        /// <summary>
        /// Get the currently active build profile, or null if using platform default.
        /// </summary>
        private BuildProfileOperationResult ExecuteGetActive()
        {
            var result = new BuildProfileOperationResult { operation = "get-active" };

            var active = BuildProfile.GetActiveBuildProfile();
            if (active == null)
            {
                result.profile = null;
                result.success = true;
                result.message = "No custom build profile active; using platform default.";
                return result;
            }

            result.profile = BuildDetailedInfo(active);
            result.success = true;
            result.message = $"Active profile: {result.profile.name} ({result.profile.platform})";
            return result;
        }

        /// <summary>
        /// Set the active build profile by asset path.
        /// </summary>
        private BuildProfileOperationResult ExecuteSetActive(BuildProfileOperationParams parameters)
        {
            var result = new BuildProfileOperationResult { operation = "set-active" };

            if (Application.isBatchMode)
            {
                result.success = false;
                result.message = "Cannot switch build profiles in batch mode. " +
                                 "Use the -activeBuildProfile CLI argument when launching Unity instead.";
                return result;
            }

            if (string.IsNullOrEmpty(parameters.profilePath))
            {
                result.success = false;
                result.message = "profilePath is required for set-active operation";
                return result;
            }

            if (!parameters.profilePath.StartsWith("Assets/"))
            {
                result.success = false;
                result.message = $"Invalid profile path: '{parameters.profilePath}'. " +
                                 "Asset paths must start with 'Assets/'.";
                return result;
            }

            var profile = AssetDatabase.LoadAssetAtPath<BuildProfile>(parameters.profilePath);
            if (profile == null)
            {
                result.success = false;
                result.message = $"Build profile not found at: {parameters.profilePath}";
                return result;
            }

            BuildProfile.SetActiveBuildProfile(profile);

            result.profile = new BuildProfileInfo
            {
                assetPath = parameters.profilePath,
                name = Path.GetFileNameWithoutExtension(parameters.profilePath),
                platform = profile.buildTarget.ToString(),
                isActive = true,
            };
            result.success = true;
            result.message = $"Activated build profile: {result.profile.name}";
            return result;
        }

        /// <summary>
        /// Get detailed info about a specific build profile by path.
        /// </summary>
        private BuildProfileOperationResult ExecuteGetInfo(BuildProfileOperationParams parameters)
        {
            var result = new BuildProfileOperationResult { operation = "get-info" };

            if (string.IsNullOrEmpty(parameters.profilePath))
            {
                result.success = false;
                result.message = "profilePath is required for get-info operation";
                return result;
            }

            if (!parameters.profilePath.StartsWith("Assets/"))
            {
                result.success = false;
                result.message = $"Invalid profile path: '{parameters.profilePath}'. " +
                                 "Asset paths must start with 'Assets/'.";
                return result;
            }

            var profile = AssetDatabase.LoadAssetAtPath<BuildProfile>(parameters.profilePath);
            if (profile == null)
            {
                result.success = false;
                result.message = $"Build profile not found at: {parameters.profilePath}";
                return result;
            }

            result.profile = BuildDetailedInfo(profile);
            result.success = true;
            result.message = $"Retrieved info for {result.profile.name}";
            return result;
        }

        /// <summary>
        /// Build a detailed BuildProfileInfo from a BuildProfile asset.
        /// </summary>
        private BuildProfileInfo BuildDetailedInfo(BuildProfile profile)
        {
            string assetPath = AssetDatabase.GetAssetPath(profile);
            var active = BuildProfile.GetActiveBuildProfile();

            var info = new BuildProfileInfo
            {
                assetPath = assetPath,
                name = Path.GetFileNameWithoutExtension(assetPath),
                platform = profile.buildTarget.ToString(),
                isActive = active != null && AssetDatabase.GetAssetPath(active) == assetPath,
                buildTarget = profile.buildTarget.ToString(),
                subtarget = profile.subtarget.ToString(),
            };

            // Scenes from the profile's scene list
            if (profile.scenes != null)
            {
                foreach (var scene in profile.scenes)
                {
                    if (scene.enabled && !string.IsNullOrEmpty(scene.path))
                        info.scenes.Add(scene.path);
                }
            }

            // Scripting defines
            info.scriptingDefines = profile.scriptingDefines ?? "";

            return info;
        }
    }
}
#endif

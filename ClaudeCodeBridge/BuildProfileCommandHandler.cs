#if UNITY_6000_0_OR_NEWER
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Profile;
using UnityEditor.Build.Reporting;
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
            = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
            {
                "set-active",
                "create",
                "set-scenes",
                "set-defines",
                "build",
            };

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

                if (string.Equals(parameters.operation, "create", StringComparison.OrdinalIgnoreCase))
                    return BuildProfileCreateOperation.Execute(command, parameters);

                BuildProfileOperationResult result = ExecuteOperation(parameters);

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

        private BuildProfileOperationResult ExecuteOperation(BuildProfileOperationParams parameters)
        {
            switch (parameters.operation?.ToLower())
            {
                case "list":
                    return ExecuteList();
                case "list-platforms":
                    return BuildProfilePlatformOperation.Execute();
                case "get-active":
                    return ExecuteGetActive();
                case "set-active":
                    return ExecuteSetActive(parameters);
                case "get-info":
                    return ExecuteGetInfo(parameters);
                case "get-scenes":
                    return ExecuteGetScenes(parameters);
                case "set-scenes":
                    return ExecuteSetScenes(parameters);
                case "get-defines":
                    return ExecuteGetDefines(parameters);
                case "set-defines":
                    return ExecuteSetDefines(parameters);
                case "build":
                    return ExecuteBuild(parameters);
                default:
                    return new BuildProfileOperationResult
                    {
                        operation = parameters.operation,
                        success = false,
                        message = $"Unknown operation: {parameters.operation}. " +
                                  "Supported: list, list-platforms, create, get-active, set-active, get-info, " +
                                  "get-scenes, set-scenes, get-defines, set-defines, build"
                    };
            }
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
                    platform = EditorUserBuildSettings.activeBuildTarget.ToString(),
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
                platform = EditorUserBuildSettings.activeBuildTarget.ToString(),
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

            var profile = LoadProfile(parameters, result, "get-info");
            if (profile == null)
                return result;

            result.profile = BuildDetailedInfo(profile);
            result.scenes = result.profile.sceneEntries;
            result.scriptingDefines = result.profile.scriptingDefineEntries;
            result.success = true;
            result.message = $"Retrieved info for {result.profile.name}";
            return result;
        }

        private BuildProfileOperationResult ExecuteGetScenes(BuildProfileOperationParams parameters)
        {
            var result = new BuildProfileOperationResult { operation = "get-scenes" };
            var profile = LoadProfile(parameters, result, "get-scenes");
            if (profile == null)
                return result;

            result.scenes = BuildSceneInfoList(profile.scenes);
            result.success = true;
            result.message = $"Retrieved {result.scenes.Count} scenes";
            return result;
        }

        private BuildProfileOperationResult ExecuteSetScenes(BuildProfileOperationParams parameters)
        {
            var result = new BuildProfileOperationResult { operation = "set-scenes" };
            var profile = LoadProfile(parameters, result, "set-scenes");
            if (profile == null)
                return result;

            var scenes = BuildProfileScenes(parameters, out string error);
            if (error != null)
                return Fail(result, error);

            profile.overrideGlobalScenes = true;
            profile.scenes = scenes;
            SaveProfile(profile);

            result.scenes = BuildSceneInfoList(profile.scenes);
            result.success = true;
            result.message = $"Set {result.scenes.Count} scenes";
            return result;
        }

        private BuildProfileOperationResult ExecuteGetDefines(BuildProfileOperationParams parameters)
        {
            var result = new BuildProfileOperationResult { operation = "get-defines" };
            var profile = LoadProfile(parameters, result, "get-defines");
            if (profile == null)
                return result;

            result.scriptingDefines = ToDefineList(profile.scriptingDefines);
            result.success = true;
            result.message = $"Retrieved {result.scriptingDefines.Count} scripting defines";
            return result;
        }

        private BuildProfileOperationResult ExecuteSetDefines(BuildProfileOperationParams parameters)
        {
            var result = new BuildProfileOperationResult { operation = "set-defines" };
            var profile = LoadProfile(parameters, result, "set-defines");
            if (profile == null)
                return result;

            if (parameters.scriptingDefines == null)
                return Fail(result, "scriptingDefines is required for set-defines operation");

            profile.scriptingDefines = SanitizeDefines(parameters.scriptingDefines).ToArray();
            SaveProfile(profile);

            result.scriptingDefines = ToDefineList(profile.scriptingDefines);
            result.success = true;
            result.message = $"Set {result.scriptingDefines.Count} scripting defines";
            return result;
        }

        private BuildProfileOperationResult ExecuteBuild(BuildProfileOperationParams parameters)
        {
            var result = new BuildProfileOperationResult { operation = "build" };
            var profile = LoadProfile(parameters, result, "build");
            if (profile == null)
                return result;

            if (!ValidateOutputPath(parameters.outputPath, result))
                return result;

            var scenesForBuild = profile.GetScenesForBuild();
            string[] buildScenes = EnabledScenePaths(scenesForBuild);
            if (buildScenes.Length == 0)
                return Fail(result, "Build profile has no enabled scenes to build");

            BuildReport report = BuildPipeline.BuildPlayer(BuildOptionsFor(parameters, buildScenes));
            PopulateBuildResult(result, parameters, buildScenes, scenesForBuild, report);
            return result;
        }

        /// <summary>
        /// Build a detailed BuildProfileInfo from a BuildProfile asset.
        /// </summary>
        internal static BuildProfileInfo BuildDetailedInfo(BuildProfile profile)
        {
            string assetPath = AssetDatabase.GetAssetPath(profile);
            var active = BuildProfile.GetActiveBuildProfile();

            var info = new BuildProfileInfo
            {
                assetPath = assetPath,
                name = Path.GetFileNameWithoutExtension(assetPath),
                platform = EditorUserBuildSettings.activeBuildTarget.ToString(),
                isActive = active != null && AssetDatabase.GetAssetPath(active) == assetPath,
                buildTarget = EditorUserBuildSettings.activeBuildTarget.ToString(),
                subtarget = "",
            };

            // Scenes from the profile's scene list
            if (profile.scenes != null)
            {
                foreach (var scene in profile.scenes)
                {
                    info.sceneEntries.Add(new BuildProfileSceneInfo
                    {
                        path = scene.path,
                        enabled = scene.enabled,
                    });
                    if (scene.enabled && !string.IsNullOrEmpty(scene.path))
                        info.scenes.Add(scene.path);
                }
            }

            // Scripting defines
            info.scriptingDefineEntries = ToDefineList(profile.scriptingDefines);
            info.scriptingDefines = string.Join(";", info.scriptingDefineEntries);

            return info;
        }

        private BuildProfile LoadProfile(
            BuildProfileOperationParams parameters,
            BuildProfileOperationResult result,
            string operation)
        {
            result.profilePath = parameters.profilePath;
            if (string.IsNullOrEmpty(parameters.profilePath))
            {
                Fail(result, $"profilePath is required for {operation} operation");
                return null;
            }

            if (!parameters.profilePath.StartsWith("Assets/"))
            {
                Fail(result, $"Invalid profile path: '{parameters.profilePath}'. " +
                             "Asset paths must start with 'Assets/'.");
                return null;
            }

            var profile = AssetDatabase.LoadAssetAtPath<BuildProfile>(parameters.profilePath);
            if (profile == null)
                Fail(result, $"Build profile not found at: {parameters.profilePath}");
            return profile;
        }

        private static BuildProfileOperationResult Fail(BuildProfileOperationResult result, string message)
        {
            result.success = false;
            result.message = message;
            return result;
        }

        private static List<BuildProfileSceneInfo> BuildSceneInfoList(
            EditorBuildSettingsScene[] scenes)
        {
            var entries = new List<BuildProfileSceneInfo>();
            if (scenes == null)
                return entries;

            foreach (var scene in scenes)
                entries.Add(new BuildProfileSceneInfo { path = scene.path, enabled = scene.enabled });
            return entries;
        }

        private static EditorBuildSettingsScene[] BuildProfileScenes(
            BuildProfileOperationParams parameters,
            out string error)
        {
            error = null;
            if (parameters.scenes == null)
            {
                error = "scenes is required for set-scenes operation";
                return new EditorBuildSettingsScene[0];
            }

            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var scenes = new List<EditorBuildSettingsScene>();
            AddScenes(scenes, seen, parameters.scenes, true, ref error);
            AddScenes(scenes, seen, parameters.disabledScenes, false, ref error);
            return scenes.ToArray();
        }

        private static void AddScenes(
            List<EditorBuildSettingsScene> scenes,
            HashSet<string> seen,
            List<string> paths,
            bool enabled,
            ref string error)
        {
            if (paths == null || error != null)
                return;

            foreach (string path in paths)
            {
                if (!ValidateScenePath(path, seen, out error))
                    return;
                scenes.Add(new EditorBuildSettingsScene(path, enabled));
            }
        }

        private static bool ValidateScenePath(
            string path,
            HashSet<string> seen,
            out string error)
        {
            error = null;
            if (string.IsNullOrEmpty(path) || !path.StartsWith("Assets/"))
                error = $"Invalid scene path: '{path}'. Asset paths must start with 'Assets/'.";
            else if (AssetDatabase.LoadAssetAtPath<SceneAsset>(path) == null)
                error = $"Scene asset not found: {path}";
            else if (!seen.Add(path))
                error = $"Duplicate scene path: {path}";
            return error == null;
        }

        private static void SaveProfile(BuildProfile profile)
        {
            EditorUtility.SetDirty(profile);
            AssetDatabase.SaveAssets();
        }

        private static bool ValidateOutputPath(string outputPath, BuildProfileOperationResult result)
        {
            result.outputPath = outputPath;
            if (string.IsNullOrEmpty(outputPath))
            {
                Fail(result, "outputPath is required for build operation");
                return false;
            }

            try
            {
                string outputDir = Path.GetDirectoryName(outputPath);
                if (string.IsNullOrEmpty(outputDir))
                {
                    Fail(result, "Invalid outputPath: no directory specified");
                    return false;
                }

                if (!Directory.Exists(outputDir))
                    Directory.CreateDirectory(outputDir);
                return true;
            }
            catch (Exception ex)
            {
                Fail(result, $"Invalid outputPath: {ex.Message}");
                return false;
            }
        }

        private static List<string> ToDefineList(string[] defines)
        {
            return defines == null ? new List<string>() : SanitizeDefines(defines).ToList();
        }

        private static IEnumerable<string> SanitizeDefines(IEnumerable<string> defines)
        {
            return defines
                .Where(define => !string.IsNullOrWhiteSpace(define))
                .Select(define => define.Trim())
                .Distinct(StringComparer.Ordinal);
        }

        private static string[] EnabledScenePaths(EditorBuildSettingsScene[] scenes)
        {
            return (scenes ?? new EditorBuildSettingsScene[0])
                .Where(scene => scene.enabled && !string.IsNullOrEmpty(scene.path))
                .Select(scene => scene.path)
                .ToArray();
        }

        private static BuildPlayerOptions BuildOptionsFor(
            BuildProfileOperationParams parameters,
            string[] buildScenes)
        {
            BuildOptions options = BuildOptions.None;
            if (parameters.development)
                options |= BuildOptions.Development;
            if (parameters.autoRunPlayer)
                options |= BuildOptions.AutoRunPlayer;

            return new BuildPlayerOptions
            {
                scenes = buildScenes,
                locationPathName = parameters.outputPath,
                target = EditorUserBuildSettings.activeBuildTarget,
                options = options,
            };
        }

        private static void PopulateBuildResult(
            BuildProfileOperationResult result,
            BuildProfileOperationParams parameters,
            string[] buildScenes,
            EditorBuildSettingsScene[] profileScenes,
            BuildReport report)
        {
            result.profilePath = parameters.profilePath;
            result.outputPath = parameters.outputPath;
            result.scenes = BuildSceneInfoList(profileScenes);
            result.success = report.summary.result == BuildResult.Succeeded;
            result.message = $"Build {report.summary.result}. " +
                             $"Scenes: {buildScenes.Length}, " +
                             $"Size: {report.summary.totalSize / (1024.0 * 1024.0):F2} MB";
            BuildProfileBuildHelpers.PopulateFromReport(result, report);
        }
    }
}
#endif

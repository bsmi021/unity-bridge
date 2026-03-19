using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for Unity build operations.
    ///
    /// This handler provides build automation and settings inspection capabilities,
    /// allowing Claude Code to trigger builds, validate configurations, and retrieve
    /// build settings without opening the Unity Editor UI.
    ///
    /// Supported operations:
    /// - "build": Trigger a build with specified settings (async, returns "running" immediately)
    /// - "get-settings": Get current build settings and configuration
    /// - "validate": Validate build configuration without building
    /// - "get-target": Get current active build target
    ///
    /// Command JSON format:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "build-operation",
    ///   "timestamp": "2025-10-06T12:00:00Z",
    ///   "parametersJson": "{\"operation\":\"get-settings\"}"
    /// }
    /// </summary>
    public class BuildOperationCommandHandler : ICommandHandler
    {
        public string CommandType => "build-operation";

        private static Dictionary<string, BuildContext> _activeBuilds = new Dictionary<string, BuildContext>();

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                // Parse parameters
                var parameters = JsonUtility.FromJson<BuildOperationParams>(command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new BuildOperationParams();

                BridgeLogger.LogDebug($"Executing operation: {parameters.operation}");

                // Route to appropriate operation handler
                switch (parameters.operation?.ToLower())
                {
                    case "build":
                        return ExecuteBuild(command, parameters);

                    case "get-settings":
                        return GetBuildSettings(command);

                    case "validate":
                        return ValidateBuildConfiguration(command, parameters);

                    case "get-target":
                        return GetBuildTarget(command);

                    default:
                        return BridgeResponse.Error(
                            command.commandId,
                            command.commandType,
                            $"Unknown operation: {parameters.operation}. Valid operations: build, get-settings, validate, get-target"
                        );
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        #region Build Operation

        /// <summary>
        /// Execute a build operation asynchronously.
        /// Returns "running" status immediately, final result written when build completes.
        /// </summary>
        private BridgeResponse ExecuteBuild(BridgeCommand command, BuildOperationParams parameters)
        {
            try
            {
                // Parse build target
                BuildTarget buildTarget = EditorUserBuildSettings.activeBuildTarget;
                if (!string.IsNullOrEmpty(parameters.target))
                {
                    if (!Enum.TryParse(parameters.target, true, out buildTarget))
                    {
                        return BridgeResponse.Error(
                            command.commandId,
                            command.commandType,
                            $"Invalid build target: {parameters.target}"
                        );
                    }
                }

                // Validate output path
                string outputPath = parameters.outputPath;
                if (string.IsNullOrEmpty(outputPath))
                {
                    // Generate default output path
                    string projectPath = Directory.GetParent(Application.dataPath).FullName;
                    string buildFolder = Path.Combine(projectPath, "Builds", buildTarget.ToString());
                    Directory.CreateDirectory(buildFolder);

                    string extension = GetBuildExtension(buildTarget);
                    outputPath = Path.Combine(buildFolder, $"Build{extension}");
                }

                // Ensure output directory exists
                string outputDir = Path.GetDirectoryName(outputPath);
                if (!Directory.Exists(outputDir))
                {
                    Directory.CreateDirectory(outputDir);
                }

                // Get scenes from build settings
                var sceneList = EditorBuildSettings.scenes
                    .Where(scene => scene.enabled)
                    .Select(scene => scene.path)
                    .ToArray();

                if (sceneList.Length == 0)
                {
                    return BridgeResponse.Error(
                        command.commandId,
                        command.commandType,
                        "No scenes enabled in build settings. Add scenes via File > Build Settings."
                    );
                }

                // Configure build options
                BuildPlayerOptions buildOptions = new BuildPlayerOptions
                {
                    scenes = sceneList,
                    locationPathName = outputPath,
                    target = buildTarget,
                    options = parameters.development ? BuildOptions.Development : BuildOptions.None
                };

                // Store build context
                var context = new BuildContext
                {
                    CommandId = command.commandId,
                    StartTime = DateTime.UtcNow,
                    BuildTarget = buildTarget,
                    OutputPath = outputPath
                };
                _activeBuilds[command.commandId] = context;

                BridgeLogger.LogInfo($"Starting build: {buildTarget} -> {outputPath}");

                // Start build on a background thread to avoid blocking Unity
                ThreadPool.QueueUserWorkItem(state =>
                {
                    try
                    {
                        // Note: BuildPipeline.BuildPlayer must run on main thread
                        // We'll use EditorApplication.delayCall to execute on main thread
                        EditorApplication.delayCall += () =>
                        {
                            try
                            {
                                BuildReport report = BuildPipeline.BuildPlayer(buildOptions);
                                OnBuildComplete(command.commandId, report);
                            }
                            catch (Exception ex)
                            {
                                OnBuildError(command.commandId, ex);
                            }
                        };
                    }
                    catch (Exception ex)
                    {
                        OnBuildError(command.commandId, ex);
                    }
                });

                // Return "running" status immediately
                var runningData = new BuildOperationResult
                {
                    operation = "build",
                    buildTarget = buildTarget.ToString(),
                    outputPath = outputPath,
                    scenes = sceneList.ToList(),
                    success = true,
                    message = $"Build started at {context.StartTime:O}"
                };

                return BridgeResponse.Running(
                    command.commandId,
                    command.commandType,
                    JsonUtility.ToJson(runningData)
                );
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Build execution error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        /// <summary>
        /// Called when build completes successfully.
        /// Writes final success response to responses directory.
        /// </summary>
        private static void OnBuildComplete(string commandId, BuildReport report)
        {
            if (!_activeBuilds.TryGetValue(commandId, out var context))
            {
                BridgeLogger.LogError($"No context found for build: {commandId}");
                return;
            }

            try
            {
                var duration = (DateTime.UtcNow - context.StartTime).TotalSeconds;

                // Parse build report
                var result = new BuildOperationResult
                {
                    operation = "build",
                    buildTarget = context.BuildTarget.ToString(),
                    outputPath = context.OutputPath,
                    success = report.summary.result == BuildResult.Succeeded,
                    message = $"Build {report.summary.result} in {duration:F2}s. Size: {report.summary.totalSize / (1024.0 * 1024.0):F2} MB"
                };

                // Add scenes
                foreach (var step in report.steps)
                {
                    if (step.name == "Build player")
                    {
                        foreach (var message in step.messages)
                        {
                            if (message.content.StartsWith("Building scene"))
                            {
                                result.scenes.Add(message.content);
                            }
                        }
                    }
                }

                // Collect errors and warnings
                foreach (var step in report.steps)
                {
                    foreach (var message in step.messages)
                    {
                        if (message.type == LogType.Error)
                        {
                            result.errors.Add($"{message.content}");
                        }
                        else if (message.type == LogType.Warning)
                        {
                            result.warnings.Add($"{message.content}");
                        }
                    }
                }

                BridgeLogger.LogInfo($"Build completed: {report.summary.result}");

                // Write final success response
                ClaudeUnityBridge.WriteResponseStatic(
                    BridgeResponse.Success(commandId, "build-operation", JsonUtility.ToJson(result))
                );
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error processing build report: {ex}");
                ClaudeUnityBridge.WriteResponseStatic(
                    BridgeResponse.Error(commandId, "build-operation", ex.ToString())
                );
            }
            finally
            {
                _activeBuilds.Remove(commandId);
            }
        }

        /// <summary>
        /// Called when build encounters an error.
        /// Writes error response to responses directory.
        /// </summary>
        private static void OnBuildError(string commandId, Exception ex)
        {
            BridgeLogger.LogError($"Build error: {ex}");

            var result = new BuildOperationResult
            {
                operation = "build",
                success = false,
                message = $"Build failed: {ex.Message}",
                errors = new List<string> { ex.ToString() }
            };

            ClaudeUnityBridge.WriteResponseStatic(
                BridgeResponse.Error(commandId, "build-operation", JsonUtility.ToJson(result))
            );

            _activeBuilds.Remove(commandId);
        }

        /// <summary>
        /// Get the appropriate file extension for a build target.
        /// </summary>
        private string GetBuildExtension(BuildTarget target)
        {
            switch (target)
            {
                case BuildTarget.StandaloneWindows:
                case BuildTarget.StandaloneWindows64:
                    return ".exe";

                case BuildTarget.StandaloneOSX:
                    return ".app";

                case BuildTarget.StandaloneLinux64:
                    return ".x86_64";

                case BuildTarget.Android:
                    return ".apk";

                case BuildTarget.iOS:
                    return "";

                case BuildTarget.WebGL:
                    return "";

                default:
                    return "";
            }
        }

        #endregion

        #region Get Build Settings

        /// <summary>
        /// Get current build settings and configuration.
        /// Returns information about enabled scenes, build target, and options.
        /// </summary>
        private BridgeResponse GetBuildSettings(BridgeCommand command)
        {
            try
            {
                var result = new BuildOperationResult
                {
                    operation = "get-settings",
                    buildTarget = EditorUserBuildSettings.activeBuildTarget.ToString(),
                    outputPath = EditorUserBuildSettings.GetBuildLocation(EditorUserBuildSettings.activeBuildTarget),
                    success = true
                };

                // Get enabled scenes
                result.scenes = EditorBuildSettings.scenes
                    .Where(scene => scene.enabled)
                    .Select(scene => scene.path)
                    .ToList();

                // Add build settings info to message
                result.message = $"Active Build Target: {result.buildTarget}\n" +
                                $"Development Build: {EditorUserBuildSettings.development}\n" +
                                $"Enabled Scenes: {result.scenes.Count}\n" +
                                $"Scene List:\n  {string.Join("\n  ", result.scenes)}";

                BridgeLogger.LogInfo($"Retrieved build settings: {result.buildTarget}");

                return BridgeResponse.Success(command.commandId, command.commandType, JsonUtility.ToJson(result));
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error getting build settings: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        #endregion

        #region Validate Build Configuration

        /// <summary>
        /// Validate build configuration without actually building.
        /// Checks for common issues like missing scenes, invalid paths, etc.
        /// </summary>
        private BridgeResponse ValidateBuildConfiguration(BridgeCommand command, BuildOperationParams parameters)
        {
            try
            {
                var result = new BuildOperationResult
                {
                    operation = "validate",
                    buildTarget = EditorUserBuildSettings.activeBuildTarget.ToString(),
                    success = true
                };

                // Override build target if specified
                BuildTarget buildTarget = EditorUserBuildSettings.activeBuildTarget;
                if (!string.IsNullOrEmpty(parameters.target))
                {
                    if (!Enum.TryParse(parameters.target, true, out buildTarget))
                    {
                        result.errors.Add($"Invalid build target: {parameters.target}");
                        result.success = false;
                    }
                    result.buildTarget = buildTarget.ToString();
                }

                // Validate scenes
                var enabledScenes = EditorBuildSettings.scenes
                    .Where(scene => scene.enabled)
                    .ToList();

                if (enabledScenes.Count == 0)
                {
                    result.errors.Add("No scenes enabled in build settings");
                    result.success = false;
                }
                else
                {
                    result.scenes = enabledScenes.Select(s => s.path).ToList();

                    // Check if scene files exist
                    foreach (var scene in enabledScenes)
                    {
                        if (!File.Exists(scene.path))
                        {
                            result.errors.Add($"Scene file not found: {scene.path}");
                            result.success = false;
                        }
                    }
                }

                // Validate output path if specified
                if (!string.IsNullOrEmpty(parameters.outputPath))
                {
                    result.outputPath = parameters.outputPath;
                    string outputDir = Path.GetDirectoryName(parameters.outputPath);

                    if (string.IsNullOrEmpty(outputDir))
                    {
                        result.errors.Add("Invalid output path: no directory specified");
                        result.success = false;
                    }
                    else if (!Directory.Exists(outputDir))
                    {
                        result.warnings.Add($"Output directory does not exist and will be created: {outputDir}");
                    }
                }

                // Check for platform-specific requirements
                switch (buildTarget)
                {
                    case BuildTarget.Android:
                        if (string.IsNullOrEmpty(PlayerSettings.Android.keystoreName))
                        {
                            result.warnings.Add("Android keystore not configured (required for release builds)");
                        }
                        break;

                    case BuildTarget.iOS:
                        if (string.IsNullOrEmpty(PlayerSettings.iOS.appleDeveloperTeamID))
                        {
                            result.warnings.Add("iOS developer team ID not configured");
                        }
                        break;
                }

                // Build message
                if (result.success)
                {
                    result.message = $"Build configuration is valid for {result.buildTarget}\n" +
                                   $"Scenes: {result.scenes.Count}\n" +
                                   $"Warnings: {result.warnings.Count}";
                }
                else
                {
                    result.message = $"Build configuration has {result.errors.Count} error(s) for {result.buildTarget}";
                }

                BridgeLogger.LogInfo($"Validation result: {result.success} ({result.errors.Count} errors, {result.warnings.Count} warnings)");

                return BridgeResponse.Success(command.commandId, command.commandType, JsonUtility.ToJson(result));
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Validation error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        #endregion

        #region Get Build Target

        /// <summary>
        /// Get the current active build target.
        /// Simple query operation that returns immediately.
        /// </summary>
        private BridgeResponse GetBuildTarget(BridgeCommand command)
        {
            try
            {
                var result = new BuildOperationResult
                {
                    operation = "get-target",
                    buildTarget = EditorUserBuildSettings.activeBuildTarget.ToString(),
                    success = true,
                    message = $"Current build target: {EditorUserBuildSettings.activeBuildTarget}"
                };

                BridgeLogger.LogInfo($"Current build target: {result.buildTarget}");

                return BridgeResponse.Success(command.commandId, command.commandType, JsonUtility.ToJson(result));
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error getting build target: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        #endregion

        /// <summary>
        /// Context for an active build operation.
        /// </summary>
        private class BuildContext
        {
            public string CommandId;
            public DateTime StartTime;
            public BuildTarget BuildTarget;
            public string OutputPath;
        }
    }
}

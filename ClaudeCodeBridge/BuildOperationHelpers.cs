using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Partial class: validate, get-target, and BuildContext for BuildOperationCommandHandler.
    /// </summary>
    public partial class BuildOperationCommandHandler
    {
        /// <summary>
        /// Validate build configuration without actually building.
        /// </summary>
        private BridgeResponse ValidateBuildConfiguration(
            BridgeCommand command, BuildOperationParams parameters)
        {
            try
            {
                var result = new BuildOperationResult
                {
                    operation = "validate",
                    buildTarget = EditorUserBuildSettings.activeBuildTarget.ToString(),
                    success = true
                };

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
                    foreach (var scene in enabledScenes)
                    {
                        if (!File.Exists(scene.path))
                        {
                            result.errors.Add($"Scene file not found: {scene.path}");
                            result.success = false;
                        }
                    }
                }

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
                        result.warnings.Add(
                            $"Output directory does not exist and will be created: {outputDir}");
                    }
                }

                switch (buildTarget)
                {
                    case BuildTarget.Android:
                        if (string.IsNullOrEmpty(PlayerSettings.Android.keystoreName))
                            result.warnings.Add("Android keystore not configured (required for release builds)");
                        break;
                    case BuildTarget.iOS:
                        if (string.IsNullOrEmpty(PlayerSettings.iOS.appleDeveloperTeamID))
                            result.warnings.Add("iOS developer team ID not configured");
                        break;
                }

                if (result.success)
                {
                    result.message = $"Build configuration is valid for {result.buildTarget}\n" +
                                   $"Scenes: {result.scenes.Count}\n" +
                                   $"Warnings: {result.warnings.Count}";
                }
                else
                {
                    result.message =
                        $"Build configuration has {result.errors.Count} error(s) for {result.buildTarget}";
                }

                BridgeLogger.LogInfo(
                    $"Validation: {result.success} ({result.errors.Count} errors, {result.warnings.Count} warnings)");

                return BridgeResponse.Success(
                    command.commandId, command.commandType, JsonUtility.ToJson(result));
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Validation error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        /// <summary>
        /// Get the current active build target.
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
                return BridgeResponse.Success(
                    command.commandId, command.commandType, JsonUtility.ToJson(result));
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error getting build target: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private class BuildContext
        {
            public string CommandId;
            public DateTime StartTime;
            public BuildTarget BuildTarget;
            public string OutputPath;
        }
    }
}

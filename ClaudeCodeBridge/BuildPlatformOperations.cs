using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.Build;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Partial class: switch-platform, list-platforms, and extended build option helpers
    /// for BuildOperationCommandHandler.
    /// </summary>
    public partial class BuildOperationCommandHandler
    {
        // Known BuildTarget values to enumerate for list-platforms
        private static readonly BuildTarget[] KNOWN_TARGETS = new[]
        {
            BuildTarget.StandaloneWindows,
            BuildTarget.StandaloneWindows64,
            BuildTarget.StandaloneOSX,
            BuildTarget.StandaloneLinux64,
            BuildTarget.Android,
            BuildTarget.iOS,
            BuildTarget.WebGL,
            BuildTarget.tvOS,
#if UNITY_6000_0_OR_NEWER
            BuildTarget.VisionOS,
#endif
        };

        /// <summary>
        /// Switch the active build platform. This triggers a domain reload.
        /// Uses deferred response pattern: returns Running immediately, writes
        /// final response after the reload completes.
        /// </summary>
        private BridgeResponse SwitchPlatform(BridgeCommand command, BuildOperationParams parameters)
        {
            try
            {
                if (string.IsNullOrEmpty(parameters.target))
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "target is required for switch-platform operation.");
                }

                if (!Enum.TryParse(parameters.target, true, out BuildTarget newTarget))
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        $"Invalid build target: {parameters.target}. " +
                        $"Valid targets: {string.Join(", ", KNOWN_TARGETS.Select(t => t.ToString()))}");
                }

                var currentTarget = EditorUserBuildSettings.activeBuildTarget;
                if (currentTarget == newTarget)
                {
                    var noChangeResult = new BuildOperationResult
                    {
                        operation = "switch-platform",
                        buildTarget = newTarget.ToString(),
                        success = true,
                        message = $"Already on {newTarget}. No switch needed."
                    };
                    return BridgeResponse.Success(
                        command.commandId, command.commandType,
                        JsonUtility.ToJson(noChangeResult));
                }

                var group = BuildPipeline.GetBuildTargetGroup(newTarget);
                if (group == BuildTargetGroup.Unknown)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        $"Cannot determine build target group for: {newTarget}");
                }

                if (!BuildPipeline.IsBuildTargetSupported(group, newTarget))
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        $"Build target not supported (module not installed?): {newTarget}");
                }

                BridgeLogger.LogInfo($"Switching platform: {currentTarget} -> {newTarget}");

                // Schedule the deferred final response after domain reload
                var cmdId = command.commandId;
                var cmdType = command.commandType;
                var targetStr = newTarget.ToString();

                EditorApplication.delayCall += () =>
                {
                    WritePlatformSwitchResult(cmdId, cmdType, targetStr);
                };

                // Perform the switch — this may trigger domain reload
                bool switched = EditorUserBuildSettings.SwitchActiveBuildTarget(group, newTarget);

                if (!switched)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        $"SwitchActiveBuildTarget failed for {newTarget}. Check Unity console.");
                }

                // Return Running — the delayCall will write the final result
                var runningData = new BuildOperationResult
                {
                    operation = "switch-platform",
                    buildTarget = newTarget.ToString(),
                    success = true,
                    message = $"Platform switch to {newTarget} initiated. Domain reload in progress."
                };

                return BridgeResponse.Running(
                    command.commandId, command.commandType,
                    JsonUtility.ToJson(runningData));
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Switch platform error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        /// <summary>
        /// Write final response after domain reload completes.
        /// </summary>
        private static void WritePlatformSwitchResult(
            string commandId, string commandType, string targetStr)
        {
            try
            {
                var result = new BuildOperationResult
                {
                    operation = "switch-platform",
                    buildTarget = EditorUserBuildSettings.activeBuildTarget.ToString(),
                    success = true,
                    message = $"Platform switched to {EditorUserBuildSettings.activeBuildTarget}"
                };

                ClaudeUnityBridge.WriteResponseStatic(
                    BridgeResponse.Success(commandId, commandType, JsonUtility.ToJson(result)));
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error writing platform switch result: {ex}");
                ClaudeUnityBridge.WriteResponseStatic(
                    BridgeResponse.Error(commandId, commandType, ex.ToString()));
            }
        }

        /// <summary>
        /// List all known build targets and whether they are supported/active.
        /// </summary>
        private BridgeResponse ListPlatforms(BridgeCommand command)
        {
            try
            {
                var activeTarget = EditorUserBuildSettings.activeBuildTarget;
                var result = new PlatformListResult
                {
                    operation = "list-platforms",
                    activePlatform = activeTarget.ToString(),
                    success = true,
                };

                foreach (var target in KNOWN_TARGETS)
                {
                    var group = BuildPipeline.GetBuildTargetGroup(target);
                    var supported = group != BuildTargetGroup.Unknown
                        && BuildPipeline.IsBuildTargetSupported(group, target);

                    result.platforms.Add(new PlatformInfo
                    {
                        name = target.ToString(),
                        isSupported = supported,
                        isActive = target == activeTarget,
                    });
                }

                result.message = $"Active: {activeTarget}. " +
                    $"Supported: {result.platforms.Count(p => p.isSupported)}/{result.platforms.Count}";

                BridgeLogger.LogInfo(result.message);
                return BridgeResponse.Success(
                    command.commandId, command.commandType,
                    JsonUtility.ToJson(result));
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"List platforms error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        /// <summary>
        /// Apply extended build flags to BuildOptions.
        /// </summary>
        private static BuildOptions ApplyExtendedBuildOptions(
            BuildOptions opts, BuildOperationParams parameters)
        {
            if (parameters.autoRunPlayer)
                opts |= BuildOptions.AutoRunPlayer;
            if (parameters.connectProfiler)
                opts |= BuildOptions.ConnectWithProfiler;
            if (parameters.allowDebugging)
                opts |= BuildOptions.AllowDebugging;
            if (parameters.cleanBuildCache)
                opts |= BuildOptions.CleanBuildCache;
            if (parameters.detailedBuildReport)
                opts |= BuildOptions.DetailedBuildReport;
            if (parameters.buildScriptsOnly)
                opts |= BuildOptions.BuildScriptsOnly;

            var compress = parameters.compress?.ToLower();
            if (compress == "lz4")
                opts |= BuildOptions.CompressWithLz4;
            else if (compress == "lz4hc")
                opts |= BuildOptions.CompressWithLz4HC;

            return opts;
        }

        /// <summary>
        /// Apply subtarget (Server, Player) to build options if specified.
        /// </summary>
        private static void ApplySubtarget(
            ref BuildPlayerOptions buildOptions, string subtarget)
        {
            if (string.IsNullOrEmpty(subtarget))
                return;

#if UNITY_2021_2_OR_NEWER
            if (subtarget.Equals("Server", StringComparison.OrdinalIgnoreCase))
                buildOptions.subtarget = (int)StandaloneBuildSubtarget.Server;
            else if (subtarget.Equals("Player", StringComparison.OrdinalIgnoreCase))
                buildOptions.subtarget = (int)StandaloneBuildSubtarget.Player;
            else
                BridgeLogger.LogWarning($"Unknown subtarget: {subtarget}. Ignoring.");
#else
            BridgeLogger.LogWarning("Subtarget requires Unity 2021.2+. Ignoring.");
#endif
        }
    }
}

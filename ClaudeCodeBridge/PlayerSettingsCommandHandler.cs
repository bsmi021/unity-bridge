using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.Build;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for reading and modifying Unity PlayerSettings and scripting defines.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "get" - Get all player settings or a specific key
    /// 2. "set" - Set a specific player setting by key
    /// 3. "defines-list" - List scripting define symbols for a platform
    /// 4. "defines-add" - Add a scripting define symbol
    /// 5. "defines-remove" - Remove a scripting define symbol
    /// </summary>
    public class PlayerSettingsCommandHandler : ICommandHandler
    {
        public string CommandType => "player-settings-operation";

        // M2: Use NamedBuildTarget static properties directly, not FromBuildTargetGroup
        private static readonly Dictionary<string, NamedBuildTarget> PLATFORM_MAP
            = new Dictionary<string, NamedBuildTarget>(StringComparer.OrdinalIgnoreCase)
        {
            { "Standalone", NamedBuildTarget.Standalone },
            { "Android", NamedBuildTarget.Android },
            { "iOS", NamedBuildTarget.iOS },
            { "WebGL", NamedBuildTarget.WebGL },
            { "Server", NamedBuildTarget.Server },
            { "WindowsStoreApps", NamedBuildTarget.WindowsStoreApps },
        };

        // Settable keys mapped to getter/setter delegates
        private static readonly Dictionary<string, Func<string>> GETTERS
            = new Dictionary<string, Func<string>>(StringComparer.OrdinalIgnoreCase)
        {
            { "companyName", () => PlayerSettings.companyName },
            { "productName", () => PlayerSettings.productName },
            { "bundleVersion", () => PlayerSettings.bundleVersion },
        };

        private static readonly Dictionary<string, Action<string>> SETTERS
            = new Dictionary<string, Action<string>>(StringComparer.OrdinalIgnoreCase)
        {
            { "companyName", v => PlayerSettings.companyName = v },
            { "productName", v => PlayerSettings.productName = v },
            { "bundleVersion", v => PlayerSettings.bundleVersion = v },
        };

        private static readonly HashSet<string> MUTATING_OPERATIONS
            = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "set", "defines-add", "defines-remove"
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

                var parameters = JsonUtility.FromJson<PlayerSettingsOperationParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new PlayerSettingsOperationParams();

                // Guard: reject mutating operations during play mode
                if (EditorApplication.isPlaying && IsMutatingOperation(parameters.operation))
                {
                    return BridgeResponse.Error(command.commandId, CommandType,
                        "Cannot perform mutating operations during play mode. Exit play mode first.");
                }

                BridgeLogger.LogDebug($"Executing player settings operation: {parameters.operation}");

                PlayerSettingsOperationResult result;

                switch (parameters.operation?.ToLower())
                {
                    case "get":
                        result = ExecuteGet(parameters);
                        break;
                    case "set":
                        result = ExecuteSet(parameters);
                        break;
                    case "defines-list":
                        result = ExecuteDefinesList(parameters);
                        break;
                    case "defines-add":
                        result = ExecuteDefinesAdd(parameters);
                        break;
                    case "defines-remove":
                        result = ExecuteDefinesRemove(parameters);
                        break;
                    default:
                        result = new PlayerSettingsOperationResult
                        {
                            operation = parameters.operation,
                            success = false,
                            message = $"Unknown operation: {parameters.operation}. " +
                                      "Supported: get, set, defines-list, defines-add, defines-remove"
                        };
                        break;
                }

                var resultJson = JsonUtility.ToJson(result);
                BridgeLogger.LogInfo(
                    $"Player settings operation completed: {parameters.operation}, success={result.success}");

                return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"PlayerSettings error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private static bool IsMutatingOperation(string operation)
        {
            return !string.IsNullOrEmpty(operation) && MUTATING_OPERATIONS.Contains(operation);
        }

        /// <summary>
        /// Get all player settings or a specific key.
        /// </summary>
        private PlayerSettingsOperationResult ExecuteGet(PlayerSettingsOperationParams parameters)
        {
            var result = new PlayerSettingsOperationResult { operation = "get" };

            if (!string.IsNullOrEmpty(parameters.key))
            {
                return ExecuteGetSingle(parameters.key, result);
            }

            return ExecuteGetAll(result);
        }

        private PlayerSettingsOperationResult ExecuteGetSingle(
            string key, PlayerSettingsOperationResult result)
        {
            if (!GETTERS.TryGetValue(key, out var getter))
            {
                result.success = false;
                result.message = $"Unknown setting key: {key}. " +
                                 $"Supported keys: {string.Join(", ", GETTERS.Keys)}";
                return result;
            }

            result.key = key;
            result.value = getter();
            result.success = true;
            result.message = $"{key} = {result.value}";
            return result;
        }

        private PlayerSettingsOperationResult ExecuteGetAll(PlayerSettingsOperationResult result)
        {
            result.settings = new PlayerSettingsData
            {
                companyName = PlayerSettings.companyName,
                productName = PlayerSettings.productName,
                bundleVersion = PlayerSettings.bundleVersion,
                applicationIdentifier = PlayerSettings.applicationIdentifier,
                defaultIsFullScreen = PlayerSettings.defaultIsFullScreen,
                runInBackground = PlayerSettings.runInBackground,
                apiCompatibilityLevel = PlayerSettings.GetApiCompatibilityLevel(
                    NamedBuildTarget.Standalone).ToString(),
                scriptingBackend = PlayerSettings.GetScriptingBackend(
                    NamedBuildTarget.Standalone).ToString(),
                targetArchitecture = PlayerSettings.Android.targetArchitectures.ToString(),
            };

            result.success = true;
            result.message = "Retrieved 9 player settings";
            return result;
        }

        /// <summary>
        /// Set a specific player setting by key.
        /// </summary>
        private PlayerSettingsOperationResult ExecuteSet(PlayerSettingsOperationParams parameters)
        {
            var result = new PlayerSettingsOperationResult { operation = "set" };

            if (string.IsNullOrEmpty(parameters.key))
            {
                result.success = false;
                result.message = "key is required for set operation";
                return result;
            }

            if (parameters.value == null)
            {
                result.success = false;
                result.message = "value is required for set operation";
                return result;
            }

            if (!GETTERS.TryGetValue(parameters.key, out var getter) ||
                !SETTERS.TryGetValue(parameters.key, out var setter))
            {
                result.success = false;
                result.message = $"Unknown or read-only setting key: {parameters.key}. " +
                                 $"Settable keys: {string.Join(", ", SETTERS.Keys)}";
                return result;
            }

            string previousValue = getter();
            setter(parameters.value);

            result.key = parameters.key;
            result.previousValue = previousValue;
            result.newValue = parameters.value;
            result.success = true;
            result.message = $"Set {parameters.key} = {parameters.value} (was: {previousValue})";
            return result;
        }

        /// <summary>
        /// List scripting define symbols for a platform.
        /// </summary>
        private PlayerSettingsOperationResult ExecuteDefinesList(
            PlayerSettingsOperationParams parameters)
        {
            var result = new PlayerSettingsOperationResult { operation = "defines-list" };

            if (!TryResolveTarget(parameters.platform, out var target, out string error))
            {
                result.success = false;
                result.message = error;
                return result;
            }

            result.platform = parameters.platform ?? GetActivePlatformName();
            PlayerSettings.GetScriptingDefineSymbols(target, out string[] defines);

            result.defines = defines.ToList();
            result.totalCount = defines.Length;
            result.success = true;
            result.message = $"{defines.Length} scripting defines for {result.platform}";
            return result;
        }

        /// <summary>
        /// Add a scripting define symbol.
        /// </summary>
        private PlayerSettingsOperationResult ExecuteDefinesAdd(
            PlayerSettingsOperationParams parameters)
        {
            var result = new PlayerSettingsOperationResult { operation = "defines-add" };

            if (string.IsNullOrEmpty(parameters.symbol))
            {
                result.success = false;
                result.message = "symbol is required for defines-add operation";
                return result;
            }

            if (!TryResolveTarget(parameters.platform, out var target, out string error))
            {
                result.success = false;
                result.message = error;
                return result;
            }

            result.platform = parameters.platform ?? GetActivePlatformName();
            result.symbol = parameters.symbol;

            PlayerSettings.GetScriptingDefineSymbols(target, out string[] currentDefines);
            var definesList = currentDefines.ToList();

            if (definesList.Contains(parameters.symbol))
            {
                result.defines = definesList;
                result.totalCount = definesList.Count;
                result.success = true;
                result.triggeredRecompilation = false;
                result.domainReloadPending = false;
                result.message = $"{parameters.symbol} already defined for {result.platform}";
                return result;
            }

            definesList.Add(parameters.symbol);
            PlayerSettings.SetScriptingDefineSymbols(target, definesList.ToArray());

            BridgeLogger.LogWarning(
                $"Scripting defines changed — domain reload will occur. " +
                $"Added '{parameters.symbol}' to {result.platform}.");

            result.defines = definesList;
            result.totalCount = definesList.Count;
            result.triggeredRecompilation = true;
            result.domainReloadPending = true;
            result.success = true;
            result.message = $"Added {parameters.symbol} to {result.platform} defines " +
                             "(recompilation triggered). Domain reload in progress. " +
                             "Wait for bridge heartbeat to resume before sending further commands.";
            return result;
        }

        /// <summary>
        /// Remove a scripting define symbol.
        /// </summary>
        private PlayerSettingsOperationResult ExecuteDefinesRemove(
            PlayerSettingsOperationParams parameters)
        {
            var result = new PlayerSettingsOperationResult { operation = "defines-remove" };

            if (string.IsNullOrEmpty(parameters.symbol))
            {
                result.success = false;
                result.message = "symbol is required for defines-remove operation";
                return result;
            }

            if (!TryResolveTarget(parameters.platform, out var target, out string error))
            {
                result.success = false;
                result.message = error;
                return result;
            }

            result.platform = parameters.platform ?? GetActivePlatformName();
            result.symbol = parameters.symbol;

            PlayerSettings.GetScriptingDefineSymbols(target, out string[] currentDefines);
            var definesList = currentDefines.ToList();

            if (!definesList.Contains(parameters.symbol))
            {
                result.defines = definesList;
                result.totalCount = definesList.Count;
                result.success = true;
                result.triggeredRecompilation = false;
                result.domainReloadPending = false;
                result.message = $"{parameters.symbol} not found in {result.platform} defines";
                return result;
            }

            definesList.Remove(parameters.symbol);
            PlayerSettings.SetScriptingDefineSymbols(target, definesList.ToArray());

            BridgeLogger.LogWarning(
                $"Scripting defines changed — domain reload will occur. " +
                $"Removed '{parameters.symbol}' from {result.platform}.");

            result.defines = definesList;
            result.totalCount = definesList.Count;
            result.triggeredRecompilation = true;
            result.domainReloadPending = true;
            result.success = true;
            result.message = $"Removed {parameters.symbol} from {result.platform} defines " +
                             "(recompilation triggered). Domain reload in progress. " +
                             "Wait for bridge heartbeat to resume before sending further commands.";
            return result;
        }

        /// <summary>
        /// Resolve a platform string to a NamedBuildTarget. Falls back to active target.
        /// </summary>
        private bool TryResolveTarget(
            string platform, out NamedBuildTarget target, out string error)
        {
            error = null;

            if (string.IsNullOrEmpty(platform))
            {
                target = GetActiveNamedBuildTarget();
                return true;
            }

            if (PLATFORM_MAP.TryGetValue(platform, out target))
            {
                return true;
            }

            target = default;
            error = $"Unknown platform: {platform}. " +
                    $"Supported platforms: {string.Join(", ", PLATFORM_MAP.Keys)}";
            return false;
        }

        private static NamedBuildTarget GetActiveNamedBuildTarget()
        {
            var activeBuildTarget = EditorUserBuildSettings.activeBuildTarget;
            foreach (var kvp in PLATFORM_MAP)
            {
                // Match by checking if the build target name contains the platform key
                if (activeBuildTarget.ToString().Contains(kvp.Key, StringComparison.OrdinalIgnoreCase))
                    return kvp.Value;
            }
            return NamedBuildTarget.Standalone;
        }

        private static string GetActivePlatformName()
        {
            var activeBuildTarget = EditorUserBuildSettings.activeBuildTarget;
            foreach (var kvp in PLATFORM_MAP)
            {
                if (activeBuildTarget.ToString().Contains(kvp.Key, StringComparison.OrdinalIgnoreCase))
                    return kvp.Key;
            }
            return "Standalone";
        }
    }
}

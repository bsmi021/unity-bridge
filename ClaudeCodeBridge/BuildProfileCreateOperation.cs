#if UNITY_6000_0_OR_NEWER
using System;
using UnityEditor;
using UnityEditor.Build.Profile;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    internal static class BuildProfileCreateOperation
    {
        internal static BridgeResponse Execute(
            BridgeCommand command,
            BuildProfileOperationParams parameters)
        {
#if UNITY_6000_5_OR_NEWER
            if (string.IsNullOrWhiteSpace(parameters.profileName))
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "profileName is required for create operation");
            if (string.IsNullOrWhiteSpace(parameters.platformId))
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "platformId is required for create operation");
            if (!GUID.TryParse(parameters.platformId, out var platformId)
                || platformId.Empty())
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Invalid build profile platform GUID: '{parameters.platformId}'.");
            }

            var callback = ScriptableObject.CreateInstance<BuildProfileCreateCallback>();
            callback.hideFlags = HideFlags.HideAndDontSave;
            callback.Initialize(command.commandId, command.commandType);
            try
            {
                var profile = BuildProfile.CreateBuildProfile(
                    platformId,
                    parameters.profileName,
                    callback.OnProfileReady);
                callback.Begin(profile);
            }
            catch
            {
                UnityEngine.Object.DestroyImmediate(callback);
                throw;
            }

            var running = new BuildProfileOperationResult
            {
                operation = "create",
                success = true,
                message = $"Creating build profile '{parameters.profileName}'; awaiting Unity callback."
            };
            return BridgeResponse.Running(
                command.commandId, command.commandType, JsonUtility.ToJson(running));
#else
            return BridgeResponse.Error(command.commandId, command.commandType,
                "Build profile creation requires Unity 6.5 or newer.");
#endif
        }

#if UNITY_6000_5_OR_NEWER
        internal static void WriteCreateResult(
            string commandId,
            string commandType,
            BuildProfile profile,
            string completionSource)
        {
            try
            {
                if (profile == null)
                {
                    ClaudeUnityBridge.WriteResponseStatic(BridgeResponse.Error(
                        commandId, commandType, "Unity returned no created build profile."));
                    return;
                }

                AssetDatabase.SaveAssets();
                var info = BuildProfileCommandHandler.BuildDetailedInfo(profile);
                var result = new BuildProfileOperationResult
                {
                    operation = "create",
                    success = true,
                    profile = info,
                    profilePath = info.assetPath,
                    completionSource = completionSource,
                    message = $"Created build profile: {info.name} ({completionSource})"
                };
                ClaudeUnityBridge.WriteResponseStatic(BridgeResponse.Success(
                    commandId, commandType, JsonUtility.ToJson(result)));
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Build profile create callback failed: {ex}");
                ClaudeUnityBridge.WriteResponseStatic(
                    BridgeResponse.Error(commandId, commandType, ex.ToString()));
            }
        }
#endif
    }
}
#endif

using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for Unity Addressables package operations.
    /// All operations are wrapped in try/catch to handle the case where
    /// the Addressables package is not installed.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "list-groups"      - List all Addressable groups
    /// 2. "build"            - Build Addressable content
    /// 3. "clean-cache"      - Clean build cache
    /// 4. "mark-addressable" - Mark an asset as addressable
    /// 5. "set-address"      - Set an asset's address key
    /// </summary>
    public class AddressablesCommandHandler : ICommandHandler
    {
        public string CommandType => "addressables";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Cannot perform Addressables operations while scripts are compiling.");
                }

                var parameters = JsonUtility.FromJson<AddressablesParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new AddressablesParams();

                BridgeLogger.LogDebug($"Executing addressables operation: {parameters.operation}");

                return DispatchOperation(command, parameters);
            }
            catch (Exception ex)
            {
                // Check if this is a missing type/assembly error
                if (ex is TypeLoadException || ex is System.IO.FileNotFoundException)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Addressables package not installed. "
                        + "Install via Package Manager: com.unity.addressables");
                }
                BridgeLogger.LogError($"Addressables operation error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse DispatchOperation(BridgeCommand command, AddressablesParams p)
        {
            // Attempt to load the Addressables types dynamically
            Type settingsType = Type.GetType(
                "UnityEditor.AddressableAssets.AddressableAssetSettingsDefaultObject, "
                + "Unity.Addressables.Editor");

            if (settingsType is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "Addressables package not installed. "
                    + "Install via Package Manager: com.unity.addressables");
            }

            switch (p.operation?.ToLower())
            {
                case "list-groups":
                    return ExecuteListGroups(command, settingsType);
                case "build":
                    return ExecuteBuild(command, settingsType);
                case "clean-cache":
                    return ExecuteCleanCache(command, settingsType);
                case "mark-addressable":
                    return ExecuteMarkAddressable(command, p, settingsType);
                case "set-address":
                    return ExecuteSetAddress(command, p, settingsType);
                default:
                    return BridgeResponse.Error(
                        command.commandId, command.commandType,
                        $"Unknown addressables operation: {p.operation}. "
                        + "Supported: list-groups, build, clean-cache, "
                        + "mark-addressable, set-address");
            }
        }

        private BridgeResponse ExecuteListGroups(BridgeCommand command, Type settingsType)
        {
            var settings = GetSettings(settingsType);
            if (settings is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "Addressable settings not initialized. Open Window > Asset Management > Addressables.");
            }

            var groupsProp = settings.GetType().GetProperty("groups");
            var groups = groupsProp?.GetValue(settings) as System.Collections.IList;

            var groupInfos = new List<AddressableGroupInfo>();
            if (groups is not null)
            {
                foreach (var group in groups)
                {
                    var nameProp = group.GetType().GetProperty("Name");
                    var guidProp = group.GetType().GetProperty("Guid");
                    var entriesProp = group.GetType().GetProperty("entries");
                    var entries = entriesProp?.GetValue(group) as System.Collections.IList;

                    groupInfos.Add(new AddressableGroupInfo
                    {
                        name = nameProp?.GetValue(group)?.ToString() ?? "Unknown",
                        guid = guidProp?.GetValue(group)?.ToString() ?? "",
                        entryCount = entries?.Count ?? 0
                    });
                }
            }

            var result = new AddressablesListResult
            {
                operation = "list-groups",
                groups = groupInfos,
                success = true,
                message = $"Found {groupInfos.Count} addressable groups"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteBuild(BridgeCommand command, Type settingsType)
        {
            if (EditorApplication.isPlaying)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "Cannot build Addressables while in Play mode.");
            }

            // Use reflection to call AddressableAssetSettings.BuildPlayerContent()
            Type builderType = Type.GetType(
                "UnityEditor.AddressableAssets.Settings.AddressableAssetSettings, "
                + "Unity.Addressables.Editor");
            if (builderType is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "Cannot find Addressable build API.");
            }

            var buildMethod = builderType.GetMethod("BuildPlayerContent",
                System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static);
            if (buildMethod is not null)
                buildMethod.Invoke(null, null);

            var result = new AddressablesResult
            {
                operation = "build",
                success = true,
                message = "Addressable content build started"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteCleanCache(BridgeCommand command, Type settingsType)
        {
            Type builderType = Type.GetType(
                "UnityEditor.AddressableAssets.Settings.AddressableAssetSettings, "
                + "Unity.Addressables.Editor");
            if (builderType is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "Cannot find Addressable build API.");
            }

            var cleanMethod = builderType.GetMethod("CleanPlayerContent",
                System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static);
            if (cleanMethod is not null)
                cleanMethod.Invoke(null, null);

            var result = new AddressablesResult
            {
                operation = "clean-cache",
                success = true,
                message = "Addressable build cache cleaned"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteMarkAddressable(
            BridgeCommand command, AddressablesParams p, Type settingsType)
        {
            if (string.IsNullOrEmpty(p.assetPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "assetPath is required for mark-addressable operation.");
            }

            var settings = GetSettings(settingsType);
            if (settings is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "Addressable settings not initialized.");
            }

            string guid = AssetDatabase.AssetPathToGUID(p.assetPath);
            if (string.IsNullOrEmpty(guid))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Asset not found at path: {p.assetPath}");
            }

            // Use reflection: settings.CreateOrMoveEntry(guid, defaultGroup)
            var defaultGroupProp = settings.GetType().GetProperty("DefaultGroup");
            var defaultGroup = defaultGroupProp?.GetValue(settings);
            if (defaultGroup is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "No default Addressable group found.");
            }

            var createMethod = settings.GetType().GetMethod("CreateOrMoveEntry",
                new[] { typeof(string), defaultGroup.GetType() });
            if (createMethod is not null)
                createMethod.Invoke(settings, new object[] { guid, defaultGroup });

            var result = new AddressablesResult
            {
                operation = "mark-addressable",
                assetPath = p.assetPath,
                success = true,
                message = $"Asset '{p.assetPath}' marked as addressable"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private BridgeResponse ExecuteSetAddress(
            BridgeCommand command, AddressablesParams p, Type settingsType)
        {
            if (string.IsNullOrEmpty(p.assetPath) || string.IsNullOrEmpty(p.address))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "assetPath and address are required for set-address operation.");
            }

            var settings = GetSettings(settingsType);
            if (settings is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "Addressable settings not initialized.");
            }

            string guid = AssetDatabase.AssetPathToGUID(p.assetPath);
            var findMethod = settings.GetType().GetMethod("FindAssetEntry",
                new[] { typeof(string) });
            var entry = findMethod?.Invoke(settings, new object[] { guid });
            if (entry is null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Asset '{p.assetPath}' is not addressable. Mark it first.");
            }

            var addressProp = entry.GetType().GetProperty("address");
            addressProp?.SetValue(entry, p.address);

            var result = new AddressablesResult
            {
                operation = "set-address",
                assetPath = p.assetPath,
                address = p.address,
                success = true,
                message = $"Address set to '{p.address}' for '{p.assetPath}'"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        // -----------------------------------------------------------------
        // Helpers
        // -----------------------------------------------------------------

        private static object GetSettings(Type settingsType)
        {
            var settingsProp = settingsType.GetProperty("Settings",
                System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static);
            return settingsProp?.GetValue(null);
        }
    }

    // -----------------------------------------------------------------
    // Models
    // -----------------------------------------------------------------

    [Serializable]
    public class AddressablesParams
    {
        public string operation;
        public string assetPath;
        public string address;
        public string groupName;
    }

    [Serializable]
    public class AddressablesResult
    {
        public string operation;
        public string assetPath;
        public string address;
        public bool success;
        public string message;
    }

    [Serializable]
    public class AddressableGroupInfo
    {
        public string name;
        public string guid;
        public int entryCount;
    }

    [Serializable]
    public class AddressablesListResult
    {
        public string operation;
        public List<AddressableGroupInfo> groups = new List<AddressableGroupInfo>();
        public bool success;
        public string message;
    }
}

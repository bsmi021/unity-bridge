using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for read-only VisualEffectAsset inspection.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "get-info" - List connected event names and exposed properties for a
    ///                 VisualEffectAsset, resolved by asset path or GUID.
    ///
    /// Uses pure reflection against com.unity.visualeffectgraph (no compile-time
    /// dependency) so ClaudeCodeBridge still compiles in projects that do not
    /// have the VFX Graph package installed, mirroring EntitiesCommandHandler
    /// and AdaptivePerformanceCommandHandler.
    /// </summary>
    public class VfxCommandHandler : ICommandHandler
    {
        private const string PackageName = "com.unity.visualeffectgraph";
        private const string VfxAssetTypeName = "UnityEngine.VFX.VisualEffectAsset";
        private const string VfxExposedPropertyTypeName = "UnityEngine.VFX.VFXExposedProperty";

        public string CommandType => "vfx-asset";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<VfxParams>(
                    command.parametersJson ?? "{}") ?? new VfxParams();

                BridgeLogger.LogDebug($"Executing vfx operation: {parameters.operation}");

                switch (parameters.operation?.ToLowerInvariant())
                {
                    case "get-info":
                        return ExecuteGetInfo(command, parameters);
                    default:
                        return BridgeResponse.Error(
                            command.commandId, command.commandType,
                            $"Unknown vfx operation: {parameters.operation}. "
                            + "Supported: get-info");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Vfx operation error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse ExecuteGetInfo(BridgeCommand command, VfxParams p)
        {
            if (!IsPackageAvailable())
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "VFX Graph package (com.unity.visualeffectgraph) is not installed.");
            }

            bool hasAssetPath = !string.IsNullOrEmpty(p.assetPath);
            bool hasGuid = !string.IsNullOrEmpty(p.guid);
            if (hasAssetPath == hasGuid)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "Exactly one of assetPath or guid must be provided.");
            }

            string assetPath = hasAssetPath ? p.assetPath : AssetDatabase.GUIDToAssetPath(p.guid);
            if (string.IsNullOrEmpty(assetPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Could not resolve asset path for GUID: {p.guid}");
            }

            Type vfxAssetType = FindType(VfxAssetTypeName);
            Type exposedPropertyType = FindType(VfxExposedPropertyTypeName);
            if (vfxAssetType == null || exposedPropertyType == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "VFX Graph API types could not be found even though the package is installed.");
            }

            UnityEngine.Object asset = AssetDatabase.LoadAssetAtPath(assetPath, vfxAssetType);
            if (asset == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"No VisualEffectAsset found at path: {assetPath}");
            }

            var result = new VfxAssetInfoResult
            {
                operation = "get-info",
                assetPath = assetPath,
                eventNames = InvokeGetEvents(asset, vfxAssetType),
                exposedProperties = InvokeGetExposedProperties(asset, vfxAssetType, exposedPropertyType),
                success = true,
                message = $"Retrieved VFX asset info for: {assetPath}"
            };

            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private static List<string> InvokeGetEvents(UnityEngine.Object asset, Type vfxAssetType)
        {
            var names = new List<string>();
            MethodInfo method = vfxAssetType.GetMethod("GetEvents", new[]
            {
                typeof(List<string>).MakeByRefType()
            });
            if (method == null) return names;

            var args = new object[] { null };
            method.Invoke(asset, args);
            if (args[0] is List<string> resultNames)
                names.AddRange(resultNames);
            return names;
        }

        private static List<VfxExposedPropertyInfo> InvokeGetExposedProperties(
            UnityEngine.Object asset, Type vfxAssetType, Type exposedPropertyType)
        {
            var properties = new List<VfxExposedPropertyInfo>();
            Type listType = typeof(List<>).MakeGenericType(exposedPropertyType);
            MethodInfo method = vfxAssetType.GetMethod("GetExposedProperties", new[]
            {
                listType.MakeByRefType()
            });
            if (method == null) return properties;

            var args = new object[] { null };
            method.Invoke(asset, args);
            if (args[0] is IEnumerable exposedList)
            {
                foreach (object exposed in exposedList)
                    properties.Add(BuildExposedPropertyInfo(exposed, exposedPropertyType));
            }
            return properties;
        }

        private static VfxExposedPropertyInfo BuildExposedPropertyInfo(object exposed, Type exposedPropertyType)
        {
            object nameValue = GetMemberValue(exposed, exposedPropertyType, "name");
            object typeValue = GetMemberValue(exposed, exposedPropertyType, "type");
            return new VfxExposedPropertyInfo
            {
                name = nameValue as string ?? "",
                type = (typeValue as Type)?.Name ?? ""
            };
        }

        private static object GetMemberValue(object target, Type type, string memberName)
        {
            const BindingFlags flags = BindingFlags.Public | BindingFlags.Instance;
            FieldInfo field = type.GetField(memberName, flags);
            if (field != null) return field.GetValue(target);
            PropertyInfo property = type.GetProperty(memberName, flags);
            return property != null ? property.GetValue(target) : null;
        }

        private static Type FindType(string fullName)
        {
            foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
            {
                Type type = assembly.GetType(fullName);
                if (type != null) return type;
            }
            return null;
        }

        private static bool IsPackageAvailable()
        {
            string root = Directory.GetParent(Application.dataPath)?.FullName;
            if (string.IsNullOrEmpty(root)) return false;
            if (Directory.Exists(Path.Combine(root, "Packages", PackageName))) return true;
            string manifest = Path.Combine(root, "Packages", "manifest.json");
            return File.Exists(manifest) && File.ReadAllText(manifest).Contains(PackageName);
        }
    }

    // -----------------------------------------------------------------
    // Models
    // -----------------------------------------------------------------

    [Serializable]
    public class VfxParams
    {
        public string operation;
        public string assetPath;
        public string guid;
    }

    [Serializable]
    public class VfxAssetInfoResult
    {
        public string operation;
        public string assetPath;
        public List<string> eventNames = new List<string>();
        public List<VfxExposedPropertyInfo> exposedProperties = new List<VfxExposedPropertyInfo>();
        public bool success;
        public string message;
    }

    [Serializable]
    public class VfxExposedPropertyInfo
    {
        public string name;
        public string type;
    }
}

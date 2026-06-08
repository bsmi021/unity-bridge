using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    public class AdaptivePerformanceCommandHandler : ICommandHandler
    {
        private const string PackageName = "com.unity.adaptiveperformance";
        private const string GeneralSettingsType =
            "UnityEngine.AdaptivePerformance.AdaptivePerformanceGeneralSettings";
        private const string ProfileType =
            "UnityEngine.AdaptivePerformance.AdaptivePerformanceScalerProfile";

        public string CommandType => "adaptive-performance";

        public BridgeResponse Execute(BridgeCommand command)
        {
            string operation = "availability";
            try
            {
                var p = JsonUtility.FromJson<AdaptivePerformanceParams>(
                    command.parametersJson ?? "{}") ?? new AdaptivePerformanceParams();
                operation = string.IsNullOrEmpty(p.operation)
                    ? "availability"
                    : p.operation.ToLowerInvariant();

                switch (operation)
                {
                    case "availability":
                        return Reply(command, Availability(operation));
                    case "settings":
                        return Reply(command, Settings(operation));
                    case "list-profiles":
                        return Reply(command, ListProfiles(operation, p));
                    case "inspect-profile":
                        return Reply(command, InspectProfile(operation, p));
                    default:
                        return Reply(command, Fail(operation,
                            "Unknown operation. Supported: availability, settings, "
                            + "list-profiles, inspect-profile"));
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Adaptive Performance error: {ex}");
                return Reply(command, Fail(operation, ex.ToString()));
            }
        }

        private static BridgeResponse Reply(
            BridgeCommand command, AdaptivePerformanceResult result)
        {
            string json = JsonUtility.ToJson(result);
            if (result.success) return BridgeResponse.Success(command.commandId, command.commandType, json);
            return BridgeResponse.Error(command.commandId, command.commandType, result.message);
        }

        private static AdaptivePerformanceResult Availability(string operation)
        {
            Type generalType = FindType(GeneralSettingsType);
            var result = BaseResult(operation, generalType);
            result.settingsAvailable = GetGeneralSettings(generalType) != null;
            result.profileCount = FindProfileAssets(false).Count;
            result.message = result.apiAvailable
                ? "Adaptive Performance API is available."
                : "Adaptive Performance API is not available.";
            return result;
        }

        private static AdaptivePerformanceResult Settings(string operation)
        {
            Type generalType = FindType(GeneralSettingsType);
            if (generalType == null) return Unavailable(operation);

            var result = BaseResult(operation, generalType);
            result.settings = BuildSettings(GetGeneralSettings(generalType));
            result.settingsAvailable = result.settings.generalAvailable;
            result.message = result.settingsAvailable
                ? "Read Adaptive Performance settings."
                : "Adaptive Performance settings asset is not configured.";
            return result;
        }

        private static AdaptivePerformanceResult ListProfiles(
            string operation, AdaptivePerformanceParams p)
        {
            Type generalType = FindType(GeneralSettingsType);
            if (generalType == null) return Unavailable(operation);

            var result = BaseResult(operation, generalType);
            result.profiles = FindProfileAssets(p.includeScalers);
            result.profileCount = result.profiles.Count;
            result.message = $"Found {result.profileCount} Adaptive Performance profile(s).";
            return result;
        }

        private static AdaptivePerformanceResult InspectProfile(
            string operation, AdaptivePerformanceParams p)
        {
            Type generalType = FindType(GeneralSettingsType);
            if (generalType == null) return Unavailable(operation);
            if (string.IsNullOrEmpty(p.assetPath))
                return Fail(operation, "assetPath is required.");

            var asset = AssetDatabase.LoadAssetAtPath<UnityEngine.Object>(p.assetPath);
            if (!IsProfile(asset)) return Fail(operation, $"Scaler profile not found: {p.assetPath}");

            var result = BaseResult(operation, generalType);
            result.profile = BuildProfile(asset, p.assetPath, p.includeScalers);
            result.profileCount = 1;
            result.message = $"Inspected Adaptive Performance profile: {p.assetPath}";
            return result;
        }

        private static AdaptivePerformanceSettingsInfo BuildSettings(object general)
        {
            var info = new AdaptivePerformanceSettingsInfo();
            if (general == null) return info;

            object manager = GetValue(general, "Manager");
            info.generalAvailable = true;
            info.assignedSettings = ObjectName(GetValue(general, "AssignedSettings"));
            info.initManagerOnStart = Bool(GetValue(general, "InitManagerOnStart"));
            info.isProviderInitialized = Bool(GetValue(general, "IsProviderInitialized"));
            info.isProviderStarted = Bool(GetValue(general, "IsProviderStarted"));
            info.managerAvailable = manager != null;
            FillManager(info, manager);
            return info;
        }

        private static void FillManager(AdaptivePerformanceSettingsInfo info, object manager)
        {
            if (manager == null) return;
            info.automaticLoading = Bool(GetValue(manager, "automaticLoading"));
            info.automaticRunning = Bool(GetValue(manager, "automaticRunning"));
            info.isInitializationComplete = Bool(GetValue(manager, "isInitializationComplete"));
            info.activeLoader = ObjectName(GetValue(manager, "activeLoader"));
            foreach (object loader in ToList(GetValue(manager, "loaders")))
                info.loaders.Add(BuildLoader(loader));
        }

        private static AdaptivePerformanceLoaderInfo BuildLoader(object loader)
        {
            return new AdaptivePerformanceLoaderInfo
            {
                name = ObjectName(loader),
                typeName = loader?.GetType().FullName ?? "",
                initialized = Bool(GetValue(loader, "Initialized")),
                running = Bool(GetValue(loader, "Running")),
                settingsType = GetLoaderSettingsType(loader),
            };
        }

        private static string GetLoaderSettingsType(object loader)
        {
            try
            {
                object settings = loader?.GetType().GetMethod("GetSettings", Type.EmptyTypes)
                    ?.Invoke(loader, null);
                return settings?.GetType().FullName ?? "";
            }
            catch
            {
                return "";
            }
        }

        private static List<AdaptivePerformanceProfileInfo> FindProfileAssets(
            bool includeScalers)
        {
            var profiles = new List<AdaptivePerformanceProfileInfo>();
            foreach (string guid in AssetDatabase.FindAssets("t:AdaptivePerformanceScalerProfile"))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                var asset = AssetDatabase.LoadAssetAtPath<UnityEngine.Object>(path);
                if (IsProfile(asset)) profiles.Add(BuildProfile(asset, path, includeScalers));
            }
            return profiles;
        }

        private static AdaptivePerformanceProfileInfo BuildProfile(
            object profile, string path, bool includeScalers)
        {
            var addedScalers = ToList(GetValue(profile, "AddedScalers"));
            var info = new AdaptivePerformanceProfileInfo
            {
                assetPath = path,
                name = Text(FirstValue(profile, "Name", "name"), ObjectName(profile)),
                typeName = profile.GetType().FullName,
                scalerCount = addedScalers.Count,
                defaultSettings = BuildScalerSettings(GetValue(profile, "DefaultScalerSettings")),
            };
            if (includeScalers)
                foreach (object scaler in addedScalers) info.scalers.Add(BuildScalerSettings(scaler));
            return info;
        }

        private static AdaptivePerformanceScalerInfo BuildScalerSettings(object scaler)
        {
            if (scaler == null) return new AdaptivePerformanceScalerInfo();
            return new AdaptivePerformanceScalerInfo
            {
                name = Text(FirstValue(scaler, "name", "Name"), ObjectName(scaler)),
                typeName = scaler.GetType().FullName,
                enabled = Bool(FirstValue(scaler, "enabled", "Enabled")),
                scale = Float(FirstValue(scaler, "scale", "Scale")),
                visualImpact = Text(FirstValue(scaler, "visualImpact", "VisualImpact")),
                target = Text(FirstValue(scaler, "target", "Target")),
                maxLevel = Int(FirstValue(scaler, "maxLevel", "MaxLevel"), 0),
                minBound = Float(FirstValue(scaler, "minBound", "MinBound")),
                maxBound = Float(FirstValue(scaler, "maxBound", "MaxBound")),
            };
        }

        private static bool IsProfile(UnityEngine.Object asset)
        {
            return asset != null && IsProfileType(asset.GetType());
        }

        private static bool IsProfileType(Type type)
        {
            while (type != null)
            {
                if (type.FullName == ProfileType) return true;
                type = type.BaseType;
            }
            return false;
        }

        private static object GetGeneralSettings(Type generalType)
        {
            return generalType == null ? null : GetStaticValue(generalType, "Instance");
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

        private static object GetStaticValue(Type type, string name)
        {
            const BindingFlags flags = BindingFlags.Public | BindingFlags.Static;
            return (object)type.GetProperty(name, flags)?.GetValue(null)
                ?? type.GetField(name, flags)?.GetValue(null);
        }

        private static object GetValue(object target, string name)
        {
            if (target == null) return null;
            const BindingFlags flags = BindingFlags.Public | BindingFlags.Instance;
            Type type = target.GetType();
            return (object)type.GetProperty(name, flags)?.GetValue(target)
                ?? type.GetField(name, flags)?.GetValue(target);
        }

        private static object FirstValue(object target, params string[] names)
        {
            foreach (string name in names)
            {
                object value = GetValue(target, name);
                if (value != null) return value;
            }
            return null;
        }

        private static List<object> ToList(object value)
        {
            var list = new List<object>();
            if (value is IEnumerable enumerable)
                foreach (object item in enumerable)
                    if (item != null) list.Add(item);
            return list;
        }

        private static bool IsPackageAvailable()
        {
            string root = Directory.GetParent(Application.dataPath)?.FullName;
            if (string.IsNullOrEmpty(root)) return false;
            if (Directory.Exists(Path.Combine(root, "Packages", PackageName))) return true;
            string manifest = Path.Combine(root, "Packages", "manifest.json");
            return File.Exists(manifest) && File.ReadAllText(manifest).Contains(PackageName);
        }

        private static AdaptivePerformanceResult BaseResult(string operation, Type generalType)
        {
            bool apiAvailable = generalType != null;
            return new AdaptivePerformanceResult
            {
                success = true,
                operation = operation,
                packageAvailable = IsPackageAvailable() || apiAvailable,
                apiAvailable = apiAvailable,
            };
        }

        private static AdaptivePerformanceResult Unavailable(string operation)
        {
            return Fail(operation, "Adaptive Performance API is not available.");
        }

        private static AdaptivePerformanceResult Fail(string operation, string message)
        {
            Type generalType = FindType(GeneralSettingsType);
            var result = BaseResult(operation, generalType);
            result.success = false;
            result.message = message;
            return result;
        }

        private static string ObjectName(object value)
        {
            return value is UnityEngine.Object obj ? obj.name : Text(value);
        }

        private static string Text(object value, string fallback = "")
        {
            return value == null ? fallback : value.ToString();
        }

        private static bool Bool(object value)
        {
            return value is bool b && b;
        }

        private static int Int(object value, int fallback)
        {
            try { return value == null ? fallback : Convert.ToInt32(value); }
            catch { return fallback; }
        }

        private static float Float(object value)
        {
            try { return value == null ? 0f : Convert.ToSingle(value); }
            catch { return 0f; }
        }
    }

    [Serializable]
    public class AdaptivePerformanceParams
    {
        public string operation;
        public string assetPath;
        public bool includeScalers;
    }

    [Serializable]
    public class AdaptivePerformanceResult
    {
        public bool success;
        public string operation;
        public bool packageAvailable;
        public bool apiAvailable;
        public bool settingsAvailable;
        public int profileCount;
        public string message;
        public AdaptivePerformanceSettingsInfo settings;
        public AdaptivePerformanceProfileInfo profile;
        public List<AdaptivePerformanceProfileInfo> profiles =
            new List<AdaptivePerformanceProfileInfo>();
    }

    [Serializable]
    public class AdaptivePerformanceSettingsInfo
    {
        public bool generalAvailable;
        public string assignedSettings;
        public bool initManagerOnStart;
        public bool isProviderInitialized;
        public bool isProviderStarted;
        public bool managerAvailable;
        public bool automaticLoading;
        public bool automaticRunning;
        public bool isInitializationComplete;
        public string activeLoader;
        public List<AdaptivePerformanceLoaderInfo> loaders =
            new List<AdaptivePerformanceLoaderInfo>();
    }

    [Serializable]
    public class AdaptivePerformanceLoaderInfo
    {
        public string name;
        public string typeName;
        public bool initialized;
        public bool running;
        public string settingsType;
    }

    [Serializable]
    public class AdaptivePerformanceProfileInfo
    {
        public string assetPath;
        public string name;
        public string typeName;
        public int scalerCount;
        public AdaptivePerformanceScalerInfo defaultSettings;
        public List<AdaptivePerformanceScalerInfo> scalers =
            new List<AdaptivePerformanceScalerInfo>();
    }

    [Serializable]
    public class AdaptivePerformanceScalerInfo
    {
        public string name;
        public string typeName;
        public bool enabled;
        public float scale;
        public string visualImpact;
        public string target;
        public int maxLevel;
        public float minBound;
        public float maxBound;
    }
}

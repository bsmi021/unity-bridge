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
    internal static class AddressablesAdvancedHelpers
    {
        public static BridgeResponse ExecuteListProfiles(BridgeCommand command, Type settingsType)
        {
            object settings = GetSettings(settingsType);
            if (settings == null) return Error(command, "Addressable settings not initialized.");
            object profileSettings = GetValue(settings, "profileSettings");
            if (profileSettings == null) return Error(command, "Addressables profile settings not found.");

            string activeId = GetString(settings, "activeProfileId");
            var profiles = ReadProfiles(profileSettings, activeId);
            string activeName = GetProfileName(profileSettings, activeId);
            var result = new AddressablesProfilesResult
            {
                operation = "list-profiles",
                success = true,
                activeProfileId = activeId,
                activeProfileName = activeName,
                profiles = profiles,
                message = $"Found {profiles.Count} Addressables profiles"
            };
            return Success(command, result);
        }

        public static BridgeResponse ExecuteSetActiveProfile(
            BridgeCommand command, AddressablesParams p, Type settingsType)
        {
            object settings = GetSettings(settingsType);
            if (settings == null) return Error(command, "Addressable settings not initialized.");
            object profileSettings = GetValue(settings, "profileSettings");
            if (profileSettings == null) return Error(command, "Addressables profile settings not found.");

            string profileId = ResolveProfileId(profileSettings, p.profileId, p.profileName);
            if (string.IsNullOrEmpty(profileId))
                return Error(command, "profileId or profileName must match an Addressables profile.");
            if (!SetValue(settings, "activeProfileId", profileId))
                return Error(command, "Addressables activeProfileId is not writable.");

            var result = new AddressablesProfilesResult
            {
                operation = "set-active-profile",
                success = true,
                activeProfileId = profileId,
                activeProfileName = GetProfileName(profileSettings, profileId),
                profiles = ReadProfiles(profileSettings, profileId),
                message = $"Active Addressables profile set to '{profileId}'"
            };
            return Success(command, result);
        }

        public static BridgeResponse ExecuteListLabels(BridgeCommand command, Type settingsType)
        {
            object settings = GetSettings(settingsType);
            if (settings == null) return Error(command, "Addressable settings not initialized.");
            var labels = ReadLabels(settings);
            var result = new AddressablesLabelsResult
            {
                operation = "list-labels",
                success = true,
                labels = labels,
                message = $"Found {labels.Count} Addressables labels"
            };
            return Success(command, result);
        }

        public static BridgeResponse ExecuteSetLabel(
            BridgeCommand command, AddressablesParams p, Type settingsType)
        {
            if (string.IsNullOrEmpty(p.assetPath) || string.IsNullOrEmpty(p.label))
                return Error(command, "assetPath and label are required for set-label operation.");
            object settings = GetSettings(settingsType);
            if (settings == null) return Error(command, "Addressable settings not initialized.");
            object entry = FindEntry(settings, p.assetPath);
            if (entry == null) return Error(command, $"Asset '{p.assetPath}' is not addressable.");
            if (!SetEntryLabel(entry, p.label, p.enable, p.force))
                return Error(command, "AddressableAssetEntry.SetLabel API was not found.");

            var result = new AddressablesLabelsResult
            {
                operation = "set-label",
                success = true,
                assetPath = p.assetPath,
                label = p.label,
                enabled = p.enable,
                labels = ReadLabels(settings),
                message = p.enable ? $"Label '{p.label}' enabled." : $"Label '{p.label}' disabled."
            };
            return Success(command, result);
        }

        public static BridgeResponse ExecuteListSchemas(BridgeCommand command, Type settingsType)
        {
            object settings = GetSettings(settingsType);
            if (settings == null) return Error(command, "Addressable settings not initialized.");
            var groups = ReadGroupSchemas(settings);
            var result = new AddressablesSchemasResult
            {
                operation = "list-schemas",
                success = true,
                groups = groups,
                message = $"Found schemas for {groups.Count} Addressables groups"
            };
            return Success(command, result);
        }

        public static BridgeResponse ExecuteAnalyze(BridgeCommand command, AddressablesParams p, Type settingsType)
        {
            try
            {
                object settings = GetSettings(settingsType);
                if (settings == null) return Error(command, "Addressable settings not initialized.");
                var result = AnalyzeApiResult(p, settings);
                return Success(command, result);
            }
            catch (Exception ex)
            {
                var result = UnsupportedAnalyze(p, $"Addressables Analyze reflection failed: {ex.Message}");
                return Success(command, result);
            }
        }

        private static List<AddressablesProfileInfo> ReadProfiles(object profileSettings, string activeId)
        {
            var profiles = ProfilesFromNames(profileSettings, activeId);
            if (profiles.Count == 0) profiles = ProfilesFromData(profileSettings, activeId);
            return profiles;
        }

        private static List<AddressablesProfileInfo> ProfilesFromNames(object profileSettings, string activeId)
        {
            var profiles = new List<AddressablesProfileInfo>();
            object names = Invoke(profileSettings, "GetAllProfileNames");
            if (names is not IEnumerable enumerable) return profiles;
            foreach (object item in enumerable)
            {
                string name = item?.ToString();
                string id = GetProfileId(profileSettings, name);
                profiles.Add(ProfileInfo(id, name, activeId));
            }
            return profiles;
        }

        private static List<AddressablesProfileInfo> ProfilesFromData(object profileSettings, string activeId)
        {
            var profiles = new List<AddressablesProfileInfo>();
            object items = GetValue(profileSettings, "profiles") ?? GetValue(profileSettings, "Profiles");
            if (items is not IEnumerable enumerable) return profiles;
            foreach (object item in enumerable)
            {
                string id = FirstString(item, "id", "Id", "profileId", "ProfileId");
                string name = FirstString(item, "profileName", "ProfileName", "name", "Name");
                profiles.Add(ProfileInfo(id, name, activeId));
            }
            return profiles;
        }

        private static AddressablesProfileInfo ProfileInfo(string id, string name, string activeId)
        {
            return new AddressablesProfileInfo
            {
                id = id ?? "",
                name = name ?? "",
                isActive = !string.IsNullOrEmpty(id) && id == activeId
            };
        }

        private static string ResolveProfileId(object profileSettings, string profileId, string profileName)
        {
            if (!string.IsNullOrEmpty(profileId))
            {
                if (!string.IsNullOrEmpty(GetProfileName(profileSettings, profileId))) return profileId;
                if (ReadProfiles(profileSettings, profileId).Any(p => p.id == profileId)) return profileId;
                return null;
            }
            return string.IsNullOrEmpty(profileName) ? null : GetProfileId(profileSettings, profileName);
        }

        private static string GetProfileId(object profileSettings, string name)
        {
            if (string.IsNullOrEmpty(name)) return null;
            object id = Invoke(profileSettings, "GetProfileId", name);
            return id?.ToString();
        }

        private static string GetProfileName(object profileSettings, string id)
        {
            if (string.IsNullOrEmpty(id)) return null;
            object name = Invoke(profileSettings, "GetProfileName", id);
            return name?.ToString();
        }

        private static List<string> ReadLabels(object settings)
        {
            var labels = new List<string>();
            object values = Invoke(settings, "GetLabels") ?? GetValue(settings, "labels");
            if (values is IEnumerable enumerable)
            {
                foreach (object item in enumerable)
                    if (item != null) labels.Add(item.ToString());
            }
            labels.Sort(StringComparer.Ordinal);
            return labels.Distinct().ToList();
        }

        private static object FindEntry(object settings, string assetPath)
        {
            string guid = AssetDatabase.AssetPathToGUID(assetPath);
            if (string.IsNullOrEmpty(guid)) return null;
            return Invoke(settings, "FindAssetEntry", guid);
        }

        private static bool SetEntryLabel(object entry, string label, bool enable, bool force)
        {
            var methods = entry.GetType().GetMethods(BindingFlags.Public | BindingFlags.Instance)
                .Where(m => m.Name == "SetLabel").OrderByDescending(m => m.GetParameters().Length);
            foreach (var method in methods)
            {
                object[] args = SetLabelArgs(method, label, enable, force);
                if (args == null) continue;
                method.Invoke(entry, args);
                return true;
            }
            return false;
        }

        private static object[] SetLabelArgs(MethodInfo method, string label, bool enable, bool force)
        {
            var ps = method.GetParameters();
            if (ps.Length < 2 || ps[0].ParameterType != typeof(string)) return null;
            var args = new object[ps.Length];
            args[0] = label;
            args[1] = enable;
            for (int i = 2; i < ps.Length; i++)
                args[i] = ps[i].Name == "force" ? force
                    : ps[i].Name == "postEvent" ? true : DefaultValue(ps[i]);
            return args;
        }

        private static List<AddressablesGroupSchemasInfo> ReadGroupSchemas(object settings)
        {
            var groups = new List<AddressablesGroupSchemasInfo>();
            object rawGroups = GetValue(settings, "groups");
            if (rawGroups is not IEnumerable enumerable) return groups;
            foreach (object group in enumerable)
            {
                if (group == null) continue;
                groups.Add(new AddressablesGroupSchemasInfo
                {
                    name = FirstString(group, "Name", "name"),
                    guid = FirstString(group, "Guid", "guid"),
                    schemas = SchemaNames(group)
                });
            }
            return groups;
        }

        private static List<string> SchemaNames(object group)
        {
            var names = new List<string>();
            object schemas = GetValue(group, "Schemas") ?? GetValue(group, "schemas");
            if (schemas is not IEnumerable enumerable) return names;
            foreach (object schema in enumerable)
                if (schema != null) names.Add(schema.GetType().FullName ?? schema.GetType().Name);
            return names;
        }

        private static AddressablesAnalyzeResult AnalyzeApiResult(AddressablesParams p, object settings)
        {
            Type analyzeSystem = FindType("UnityEditor.AddressableAssets.Build.AnalyzeSystem");
            var rules = DiscoverAnalyzeRules(analyzeSystem);
            if (analyzeSystem == null && rules.Count == 0)
                return UnsupportedAnalyze(p, "Addressables Analyze API is not available.");
            var result = BuildAnalyzeResult(p, analyzeSystem != null, rules);
            if (!string.IsNullOrEmpty(p.analyzeRule)) RunAnalyzeRule(p, result, rules, settings);
            return result;
        }

        private static List<object> DiscoverAnalyzeRules(Type analyzeSystem)
        {
            var rules = RulesFromAnalyzeSystem(analyzeSystem);
            if (rules.Count > 0) return rules;
            return RulesFromTypes();
        }

        private static List<object> RulesFromAnalyzeSystem(Type analyzeSystem)
        {
            var rules = new List<object>();
            if (analyzeSystem == null) return rules;
            foreach (var method in analyzeSystem.GetMethods(BindingFlags.Public | BindingFlags.Static))
            {
                if (!method.Name.Contains("Rule") || method.GetParameters().Length != 0) continue;
                if (method.Invoke(null, null) is IEnumerable enumerable)
                    foreach (object rule in enumerable) if (rule != null) rules.Add(rule);
            }
            return rules;
        }

        private static List<object> RulesFromTypes()
        {
            var rules = new List<object>();
            Type baseType = FindType("UnityEditor.AddressableAssets.Build.AnalyzeRules.AnalyzeRule");
            if (baseType == null) return rules;
            foreach (Type type in SafeTypes().Where(t => IsConcreteRule(t, baseType)))
            {
                try { rules.Add(Activator.CreateInstance(type)); }
                catch { rules.Add(type); }
            }
            return rules;
        }

        private static AddressablesAnalyzeResult BuildAnalyzeResult(
            AddressablesParams p, bool apiAvailable, List<object> rules)
        {
            var result = new AddressablesAnalyzeResult
            {
                operation = "analyze",
                success = true,
                apiAvailable = apiAvailable,
                supported = rules.Count > 0,
                analyzeRule = p.analyzeRule,
                outputPath = p.outputPath,
                ruleCount = rules.Count,
                message = rules.Count > 0 ? $"Discovered {rules.Count} Analyze rules."
                    : "Addressables Analyze rules were not found."
            };
            foreach (object rule in rules) result.rules.Add(ReadRule(rule));
            return result;
        }

        private static void RunAnalyzeRule(
            AddressablesParams p, AddressablesAnalyzeResult result, List<object> rules, object settings)
        {
            object rule = rules.FirstOrDefault(r => RuleName(r) == p.analyzeRule
                || RuleTypeName(r).EndsWith(p.analyzeRule, StringComparison.Ordinal));
            if (rule == null)
            {
                result.message = $"Analyze rule not found: {p.analyzeRule}";
                return;
            }
            result.message = TryRunRule(rule, p.outputPath, settings);
            foreach (var info in result.rules)
                if (info.name == RuleName(rule) || info.typeName == RuleTypeName(rule)) info.status = result.message;
        }

        private static string TryRunRule(object rule, string outputPath, object settings)
        {
            if (rule is Type) return "Analyze rule could not be instantiated; listed only.";
            foreach (string methodName in new[] { "RefreshAnalysis", "RunAnalysis", "Run" })
            {
                var method = rule.GetType().GetMethod(methodName, BindingFlags.Public | BindingFlags.Instance);
                if (method == null) continue;
                object value = method.Invoke(rule, BuildAnalyzeArgs(method, settings));
                WriteOutput(outputPath, value);
                return $"Analyze rule executed via {methodName}.";
            }
            return "Analyze rule has no known callable run method; listed only.";
        }

        private static AddressablesAnalyzeRuleInfo ReadRule(object rule)
        {
            return new AddressablesAnalyzeRuleInfo
            {
                name = RuleName(rule),
                typeName = RuleTypeName(rule),
                canRun = rule is not Type,
                status = "available"
            };
        }

        private static string RuleName(object rule)
        {
            if (rule is Type type) return type.Name;
            return FirstString(rule, "ruleName", "RuleName", "name", "Name") ?? RuleTypeName(rule);
        }

        private static string RuleTypeName(object rule)
        {
            Type type = rule as Type ?? rule?.GetType();
            return type?.FullName ?? "";
        }

        private static void WriteOutput(string outputPath, object value)
        {
            if (string.IsNullOrEmpty(outputPath) || value == null) return;
            string directory = Path.GetDirectoryName(outputPath);
            if (!string.IsNullOrEmpty(directory)) Directory.CreateDirectory(directory);
            File.WriteAllText(outputPath, value.ToString());
        }

        private static AddressablesAnalyzeResult UnsupportedAnalyze(AddressablesParams p, string message)
        {
            return new AddressablesAnalyzeResult
            {
                operation = "analyze",
                success = true,
                apiAvailable = false,
                supported = false,
                analyzeRule = p.analyzeRule,
                outputPath = p.outputPath,
                message = message
            };
        }

        private static object GetSettings(Type settingsType)
        {
            var prop = settingsType.GetProperty("Settings", BindingFlags.Public | BindingFlags.Static);
            return prop?.GetValue(null);
        }

        private static object Invoke(object target, string name, params object[] args)
        {
            if (target == null) return null;
            var types = args.Select(a => a?.GetType() ?? typeof(object)).ToArray();
            var method = target.GetType().GetMethod(name, types)
                ?? target.GetType().GetMethod(name, BindingFlags.Public | BindingFlags.Instance);
            return method?.Invoke(target, args);
        }

        private static bool SetValue(object target, string name, object value)
        {
            var member = FindMember(target?.GetType(), name);
            if (member is PropertyInfo p && p.CanWrite) { p.SetValue(target, value); return true; }
            if (member is FieldInfo f) { f.SetValue(target, value); return true; }
            return false;
        }

        private static object GetValue(object target, string name)
        {
            var member = FindMember(target?.GetType(), name);
            if (member is PropertyInfo p) return p.GetValue(target);
            if (member is FieldInfo f) return f.GetValue(target);
            return null;
        }

        private static MemberInfo FindMember(Type type, string name)
        {
            if (type == null) return null;
            const BindingFlags flags = BindingFlags.Public | BindingFlags.Instance;
            return (MemberInfo)type.GetProperty(name, flags) ?? type.GetField(name, flags);
        }

        private static string FirstString(object target, params string[] names)
        {
            foreach (string name in names)
            {
                string value = GetString(target, name);
                if (!string.IsNullOrEmpty(value)) return value;
            }
            return null;
        }

        private static string GetString(object target, string name) => GetValue(target, name)?.ToString();

        private static object DefaultValue(ParameterInfo parameter)
        {
            return parameter.HasDefaultValue ? parameter.DefaultValue
                : parameter.ParameterType.IsValueType ? Activator.CreateInstance(parameter.ParameterType) : null;
        }

        private static object[] BuildAnalyzeArgs(MethodInfo method, object settings)
        {
            var ps = method.GetParameters();
            var args = new object[ps.Length];
            for (int i = 0; i < ps.Length; i++)
                args[i] = settings != null && ps[i].ParameterType.IsInstanceOfType(settings)
                    ? settings : DefaultValue(ps[i]);
            return args;
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

        private static IEnumerable<Type> SafeTypes()
        {
            foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
            {
                Type[] types;
                try { types = assembly.GetTypes(); }
                catch (ReflectionTypeLoadException ex) { types = ex.Types; }
                foreach (Type type in types) if (type != null) yield return type;
            }
        }

        private static bool IsConcreteRule(Type type, Type baseType) =>
            type != null && !type.IsAbstract && baseType.IsAssignableFrom(type);

        private static BridgeResponse Success<T>(BridgeCommand command, T result) =>
            BridgeResponse.Success(command.commandId, command.commandType, JsonUtility.ToJson(result));

        private static BridgeResponse Error(BridgeCommand command, string message) =>
            BridgeResponse.Error(command.commandId, command.commandType, message);
    }

    [Serializable]
    public class AddressablesProfileInfo { public string id, name; public bool isActive; }

    [Serializable]
    public class AddressablesProfilesResult
    {
        public string operation, activeProfileId, activeProfileName, message;
        public bool success;
        public List<AddressablesProfileInfo> profiles = new List<AddressablesProfileInfo>();
    }

    [Serializable]
    public class AddressablesLabelsResult
    {
        public string operation, assetPath, label, message;
        public bool success;
        public bool enabled;
        public List<string> labels = new List<string>();
    }

    [Serializable]
    public class AddressablesGroupSchemasInfo { public string name, guid; public List<string> schemas = new List<string>(); }

    [Serializable]
    public class AddressablesSchemasResult
    {
        public string operation, message;
        public bool success;
        public List<AddressablesGroupSchemasInfo> groups = new List<AddressablesGroupSchemasInfo>();
    }

    [Serializable]
    public class AddressablesAnalyzeRuleInfo { public string name, typeName, status; public bool canRun; }

    [Serializable]
    public class AddressablesAnalyzeResult
    {
        public string operation, analyzeRule, outputPath, message;
        public bool success, apiAvailable, supported;
        public int ruleCount;
        public List<AddressablesAnalyzeRuleInfo> rules = new List<AddressablesAnalyzeRuleInfo>();
    }
}

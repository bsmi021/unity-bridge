using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    public partial class LocalizationCommandHandler : ICommandHandler
    {
        private const string PackageName = "com.unity.localization";
        private const string SettingsTypeName = "UnityEngine.Localization.Settings.LocalizationSettings";
        private const string EditorSettingsTypeName =
            "UnityEditor.Localization.LocalizationEditorSettings";

        public string CommandType => "localization";

        public BridgeResponse Execute(BridgeCommand command)
        {
            string operation = "list-locales";
            try
            {
                var p = JsonUtility.FromJson<LocalizationParams>(
                    command.parametersJson ?? "{}") ?? new LocalizationParams();
                operation = string.IsNullOrEmpty(p.operation)
                    ? "list-locales"
                    : p.operation.ToLowerInvariant();

                switch (operation)
                {
                    case "list-locales":
                        return Reply(command, ListLocales(operation));
                    case "add-locale":
                        return Reply(command, AddLocale(operation, p));
                    case "remove-locale":
                        return Reply(command, RemoveLocale(operation, p));
                    case "get-selected-locale":
                        return Reply(command, GetSelectedLocale(operation));
                    case "set-selected-locale":
                        return Reply(command, SetSelectedLocale(operation, p));
                    case "create-string-table-collection":
                        return Reply(command, CreateStringTableCollection(operation, p));
                    case "get-string-table-collection":
                        return Reply(command, GetStringTableCollection(operation, p));
                    case "add-entry":
                        return Reply(command, AddEntry(operation, p));
                    case "export-csv":
                        return Reply(command, ExportCsv(operation, p));
                    case "import-csv":
                        return Reply(command, ImportCsv(operation, p));
                    case "export-xliff":
                        return Reply(command, ExportXliff(operation, p));
                    case "import-xliff":
                        return Reply(command, ImportXliff(operation, p));
                    default:
                        return Reply(command, Fail(operation,
                            "Unknown operation. Supported: list-locales, add-locale, "
                            + "remove-locale, get-selected-locale, set-selected-locale, "
                            + "create-string-table-collection, get-string-table-collection, "
                            + "add-entry, export-csv, import-csv, export-xliff, import-xliff"));
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Localization error: {ex}");
                return Reply(command, Fail(operation, ex.ToString()));
            }
        }

        private static BridgeResponse Reply(BridgeCommand command, LocalizationResult result)
        {
            string json = JsonUtility.ToJson(result);
            if (result.success) return BridgeResponse.Success(command.commandId, command.commandType, json);
            return BridgeResponse.Error(command.commandId, command.commandType, result.message);
        }

        private static LocalizationResult ListLocales(string operation)
        {
            Type editorSettingsType = FindType(EditorSettingsTypeName);
            if (editorSettingsType == null) return Unavailable(operation);

            var result = BaseResult(operation, editorSettingsType);
            object locales = InvokeStatic(editorSettingsType, "GetLocales");
            foreach (object locale in ToList(locales))
                result.locales.Add(BuildLocaleInfo(locale));

            result.message = $"Found {result.locales.Count} locale(s).";
            return result;
        }

        private static LocalizationResult AddLocale(string operation, LocalizationParams p)
        {
            Type editorSettingsType = FindType(EditorSettingsTypeName);
            if (editorSettingsType == null) return Unavailable(operation);
            if (string.IsNullOrEmpty(p.localeCode))
                return Fail(operation, "localeCode is required.");

            object existing = FindLocaleByCode(editorSettingsType, p.localeCode);
            if (existing != null)
                return Fail(operation, $"Locale already registered: {p.localeCode}");

            object locale = CreateLocale(p.localeCode);
            if (locale == null)
                return Fail(operation, $"Could not create locale for code: {p.localeCode}");

            if (!PersistLocaleAsset(locale, p.localeCode))
                return Fail(operation, $"Could not persist Locale asset for: {p.localeCode}");

            InvokeStatic(editorSettingsType, "AddLocale", new object[] { locale, false });

            var result = BaseResult(operation, editorSettingsType);
            result.locales.Add(BuildLocaleInfo(locale));
            result.message = $"Added locale: {p.localeCode}";
            return result;
        }

        private static bool PersistLocaleAsset(object locale, string localeCode)
        {
            if (locale is not UnityEngine.Object localeObject) return false;

            const string assetDir = "Assets/Localization/Locales";
            if (!AssetDatabase.IsValidFolder("Assets/Localization"))
                AssetDatabase.CreateFolder("Assets", "Localization");
            if (!AssetDatabase.IsValidFolder(assetDir))
                AssetDatabase.CreateFolder("Assets/Localization", "Locales");

            string path = AssetDatabase.GenerateUniqueAssetPath(
                $"{assetDir}/Locale-{localeCode}.asset");
            AssetDatabase.CreateAsset(localeObject, path);
            AssetDatabase.SaveAssets();
            return true;
        }

        private static LocalizationResult RemoveLocale(string operation, LocalizationParams p)
        {
            Type editorSettingsType = FindType(EditorSettingsTypeName);
            if (editorSettingsType == null) return Unavailable(operation);
            if (string.IsNullOrEmpty(p.localeCode))
                return Fail(operation, "localeCode is required.");

            object locale = FindLocaleByCode(editorSettingsType, p.localeCode);
            if (locale == null)
                return Fail(operation, $"Locale not found: {p.localeCode}");

            InvokeStatic(editorSettingsType, "RemoveLocale", new object[] { locale, false });

            var result = BaseResult(operation, editorSettingsType);
            result.message = $"Removed locale: {p.localeCode}";
            return result;
        }

        private static LocalizationResult GetSelectedLocale(string operation)
        {
            Type settingsType = FindType(SettingsTypeName);
            if (settingsType == null) return Unavailable(operation);

            object locale = GetStaticValue(settingsType, "SelectedLocale");
            var result = BaseResult(operation, settingsType);
            result.selectedLocale = LocaleCode(locale);
            result.message = string.IsNullOrEmpty(result.selectedLocale)
                ? "No locale is currently selected."
                : $"Selected locale: {result.selectedLocale}";
            return result;
        }

        private static LocalizationResult SetSelectedLocale(string operation, LocalizationParams p)
        {
            Type settingsType = FindType(SettingsTypeName);
            Type editorSettingsType = FindType(EditorSettingsTypeName);
            if (settingsType == null || editorSettingsType == null) return Unavailable(operation);
            if (string.IsNullOrEmpty(p.localeCode))
                return Fail(operation, "localeCode is required.");

            object locale = FindLocaleByCode(editorSettingsType, p.localeCode);
            if (locale == null)
                return Fail(operation, $"Locale not found: {p.localeCode}");

            SetStaticValue(settingsType, "SelectedLocale", locale);

            var result = BaseResult(operation, settingsType);
            result.selectedLocale = p.localeCode;
            result.message = $"Selected locale set to: {p.localeCode}";
            return result;
        }

        private static LocalizationLocaleInfo BuildLocaleInfo(object locale)
        {
            return new LocalizationLocaleInfo
            {
                code = LocaleCode(locale),
                name = Text(GetValue(locale, "LocaleName"))
            };
        }

        private static object FindLocaleByCode(Type editorSettingsType, string localeCode)
        {
            object locales = InvokeStatic(editorSettingsType, "GetLocales");
            foreach (object locale in ToList(locales))
                if (string.Equals(LocaleCode(locale), localeCode, StringComparison.OrdinalIgnoreCase))
                    return locale;
            return null;
        }

        private static string LocaleCode(object locale)
        {
            object identifier = GetValue(locale, "Identifier");
            object code = GetValue(identifier, "Code");
            return Text(code);
        }

        // Uses the Locale.CreateLocale(LocaleIdentifier) overload rather than the
        // Locale.CreateLocale(SystemLanguage) overload cited in verified facts, because
        // localeCode here is an arbitrary bridge-supplied string (e.g. "en", "fr", "pt-BR")
        // that does not map 1:1 onto the finite SystemLanguage enum. LocaleIdentifier has a
        // public string constructor, which is the documented way to build custom codes.
        // Signature not compile-checked in this environment; if GetMethod fails to resolve
        // (overload absent/renamed), this returns null and add-locale fails gracefully.
        private static object CreateLocale(string localeCode)
        {
            Type localeType = FindType("UnityEngine.Localization.Locale");
            Type identifierType = FindType("UnityEngine.Localization.LocaleIdentifier");
            if (localeType == null || identifierType == null) return null;

            var createMethod = localeType.GetMethod(
                "CreateLocale", BindingFlags.Public | BindingFlags.Static,
                null, new[] { identifierType }, null);
            if (createMethod == null) return null;

            var identifierCtor = identifierType.GetConstructor(new[] { typeof(string) });
            object identifier = identifierCtor?.Invoke(new object[] { localeCode });
            if (identifier == null) return null;

            return createMethod.Invoke(null, new[] { identifier });
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

        private static void SetStaticValue(Type type, string name, object value)
        {
            const BindingFlags flags = BindingFlags.Public | BindingFlags.Static;
            var property = type.GetProperty(name, flags);
            if (property != null && property.CanWrite) { property.SetValue(null, value); return; }
            type.GetField(name, flags)?.SetValue(null, value);
        }

        private static object InvokeStatic(Type type, string name, object[] args = null)
        {
            const BindingFlags flags = BindingFlags.Public | BindingFlags.Static;
            args ??= Array.Empty<object>();
            MethodInfo method = FindMethod(type, name, flags, args.Length);
            return method?.Invoke(null, args);
        }

        private static MethodInfo FindMethod(Type type, string name, BindingFlags flags, int argCount)
        {
            foreach (var method in type.GetMethods(flags))
                if (method.Name == name && method.GetParameters().Length == argCount)
                    return method;
            return null;
        }

        private static object GetValue(object target, string name)
        {
            if (target == null) return null;
            const BindingFlags flags = BindingFlags.Public | BindingFlags.Instance;
            Type type = target.GetType();
            return (object)type.GetProperty(name, flags)?.GetValue(target)
                ?? type.GetField(name, flags)?.GetValue(target);
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

        private static LocalizationResult BaseResult(string operation, Type apiType)
        {
            bool apiAvailable = apiType != null;
            return new LocalizationResult
            {
                success = true,
                operation = operation,
                packageAvailable = IsPackageAvailable() || apiAvailable,
                apiAvailable = apiAvailable,
            };
        }

        private static LocalizationResult Unavailable(string operation)
        {
            return Fail(operation, "Localization package is not installed.");
        }

        private static LocalizationResult Fail(string operation, string message)
        {
            Type apiType = FindType(SettingsTypeName);
            var result = BaseResult(operation, apiType);
            result.success = false;
            result.message = message;
            return result;
        }

        private static string Text(object value, string fallback = "")
        {
            return value == null ? fallback : value.ToString();
        }
    }
}

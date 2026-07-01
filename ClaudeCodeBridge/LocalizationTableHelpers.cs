using System;
using System.Collections.Generic;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    public partial class LocalizationCommandHandler
    {
        private static LocalizationResult CreateStringTableCollection(
            string operation, LocalizationParams p)
        {
            Type editorSettingsType = FindType(EditorSettingsTypeName);
            if (editorSettingsType == null) return Unavailable(operation);
            if (string.IsNullOrEmpty(p.tableCollectionName))
                return Fail(operation, "tableCollectionName is required.");

            const string assetDir = "Assets/Localization";
            if (!AssetDatabase.IsValidFolder(assetDir))
                AssetDatabase.CreateFolder("Assets", "Localization");

            object collection = InvokeStatic(
                editorSettingsType, "CreateStringTableCollection",
                new object[] { p.tableCollectionName, assetDir });
            if (collection == null)
                return Fail(operation, $"Could not create table collection: {p.tableCollectionName}");

            var result = BaseResult(operation, editorSettingsType);
            result.table = BuildTableInfo(collection, p.tableCollectionName);
            result.message = $"Created string table collection: {p.tableCollectionName}";
            return result;
        }

        private static LocalizationResult GetStringTableCollection(
            string operation, LocalizationParams p)
        {
            Type editorSettingsType = FindType(EditorSettingsTypeName);
            if (editorSettingsType == null) return Unavailable(operation);
            if (string.IsNullOrEmpty(p.tableCollectionName))
                return Fail(operation, "tableCollectionName is required.");

            object collection = FindCollection(editorSettingsType, p.tableCollectionName);
            if (collection == null)
                return Fail(operation, $"Table collection not found: {p.tableCollectionName}");

            var result = BaseResult(operation, editorSettingsType);
            result.table = BuildTableInfo(collection, p.tableCollectionName);
            foreach (var entry in ListEntries(collection))
                result.entries.Add(entry);
            result.message = $"Retrieved table collection: {p.tableCollectionName}";
            return result;
        }

        private static LocalizationResult AddEntry(string operation, LocalizationParams p)
        {
            Type editorSettingsType = FindType(EditorSettingsTypeName);
            if (editorSettingsType == null) return Unavailable(operation);
            if (string.IsNullOrEmpty(p.tableCollectionName) || string.IsNullOrEmpty(p.key))
                return Fail(operation, "tableCollectionName and key are required.");

            object collection = FindCollection(editorSettingsType, p.tableCollectionName);
            if (collection == null)
                return Fail(operation, $"Table collection not found: {p.tableCollectionName}");

            bool added = false;
            foreach (object table in ToList(GetValue(collection, "StringTables")))
            {
                object entry = InvokeInstance(table, "AddEntry", new object[] { p.key, p.value ?? "" });
                if (entry == null) continue;
                EditorUtility.SetDirty((UnityEngine.Object)table);
                added = true;
            }

            object sharedData = GetValue(collection, "SharedData");
            if (sharedData is UnityEngine.Object sharedObj) EditorUtility.SetDirty(sharedObj);
            AssetDatabase.SaveAssets();

            if (!added)
                return Fail(operation, $"No string tables found in collection: {p.tableCollectionName}");

            var result = BaseResult(operation, editorSettingsType);
            result.table = BuildTableInfo(collection, p.tableCollectionName);
            result.message = $"Added entry '{p.key}' to {p.tableCollectionName}";
            return result;
        }

        private static object FindCollection(Type editorSettingsType, string tableCollectionName)
        {
            foreach (object collection in ToList(InvokeStatic(editorSettingsType, "GetStringTableCollections")))
                if (string.Equals(Text(GetValue(collection, "TableCollectionName")),
                        tableCollectionName, StringComparison.Ordinal))
                    return collection;
            return null;
        }

        private static LocalizationTableInfo BuildTableInfo(object collection, string name)
        {
            var tables = ToList(GetValue(collection, "StringTables"));
            int entryCount = 0;
            foreach (object table in tables)
                entryCount += CountEntries(table);

            return new LocalizationTableInfo
            {
                tableCollectionName = name,
                tableCount = tables.Count,
                entryCount = entryCount,
            };
        }

        private static List<LocalizationEntryInfo> ListEntries(object collection)
        {
            var entries = new List<LocalizationEntryInfo>();
            foreach (object table in ToList(GetValue(collection, "StringTables")))
            {
                object identifier = GetValue(table, "LocaleIdentifier");
                string localeCode = Text(GetValue(identifier, "Code"));
                foreach (object entry in ToList(GetValue(table, "Values")))
                {
                    entries.Add(new LocalizationEntryInfo
                    {
                        key = Text(GetValue(entry, "Key")),
                        value = Text(GetValue(entry, "Value")),
                        localeCode = localeCode,
                    });
                }
            }
            return entries;
        }

        private static int CountEntries(object table)
        {
            object values = GetValue(table, "Values");
            int count = 0;
            foreach (object _ in ToList(values)) count++;
            return count;
        }

        private static object InvokeInstance(object target, string name, object[] args)
        {
            if (target == null) return null;
            const BindingFlags flags = BindingFlags.Public | BindingFlags.Instance;
            MethodInfo method = FindMethod(target.GetType(), name, flags, args.Length);
            return method?.Invoke(target, args);
        }
    }
}

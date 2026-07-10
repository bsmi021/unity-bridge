using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    internal static class ExecuteScriptResultSerializer
    {
        private const int MaxDepth = 16;
        private const int MaxItems = 10000;

        public static bool TrySerialize(
            object value,
            bool resultSet,
            string returnSchema,
            out ExecuteScriptValue serialized,
            out string message)
        {
            var visited = new HashSet<object>(ReferenceComparer.Instance);
            if (!TrySerializeValue(value, resultSet, 0, visited, out serialized, out message))
                return false;
            return MatchesSchema(serialized, resultSet, returnSchema, out message);
        }

        public static string ToLegacyScalar(ExecuteScriptValue value)
        {
            if (value == null)
                return "";
            if (value.kind == "boolean")
                return value.boolValue ? "true" : "false";
            if (value.kind == "string" || value.kind == "integer"
                || value.kind == "number" || value.kind == "enum")
            {
                return value.stringValue ?? "";
            }
            return "";
        }

        private static bool TrySerializeValue(
            object value,
            bool resultSet,
            int depth,
            HashSet<object> visited,
            out ExecuteScriptValue serialized,
            out string message)
        {
            serialized = null;
            message = "";
            if (!resultSet || value == null)
            {
                serialized = NewValue("null", value?.GetType());
                return true;
            }
            if (depth > MaxDepth)
                return Fail("Result exceeds the maximum serialization depth.", out message);

            var type = value.GetType();
            if (TrySerializeScalar(value, type, out serialized))
                return true;
            if (value is UnityEngine.Object unityObject)
                return TrySerializeUnityObject(unityObject, out serialized, out message);
            if (value is IDictionary dictionary)
                return TrySerializeDictionary(dictionary, type, depth, visited, out serialized, out message);
            if (value is IEnumerable enumerable)
                return TrySerializeCollection(enumerable, type, depth, visited, out serialized, out message);
            if (type.IsDefined(typeof(SerializableAttribute), false))
                return TrySerializeDto(value, type, depth, visited, out serialized, out message);
            return Fail($"Unsupported result type: {type.FullName}", out message);
        }

        private static bool TrySerializeScalar(
            object value, Type type, out ExecuteScriptValue serialized)
        {
            serialized = null;
            if (value is bool boolean)
            {
                serialized = NewValue("boolean", type);
                serialized.boolValue = boolean;
                return true;
            }
            if (value is string || value is char)
            {
                serialized = NewValue("string", type);
                serialized.stringValue = Convert.ToString(value, CultureInfo.InvariantCulture);
                return true;
            }
            if (type.IsEnum)
            {
                serialized = NewValue("enum", type);
                serialized.stringValue = Enum.GetName(type, value) ?? value.ToString();
                return true;
            }
            if (!IsInteger(type) && !IsNumber(type))
                return false;
            serialized = NewValue(IsInteger(type) ? "integer" : "number", type);
            serialized.stringValue = Convert.ToString(value, CultureInfo.InvariantCulture);
            return true;
        }

        private static bool TrySerializeUnityObject(
            UnityEngine.Object value,
            out ExecuteScriptValue serialized,
            out string message)
        {
            serialized = NewValue("unity-object", value.GetType());
            message = "";
            try
            {
                serialized.unityObject = new ExecuteScriptUnityObject
                {
                    objectId = ObjectId(value),
                    name = value.name,
                    type = value.GetType().FullName,
                    assetPath = AssetDatabase.GetAssetPath(value) ?? "",
                    globalObjectId = GlobalObjectId.GetGlobalObjectIdSlow(value).ToString(),
                };
                return true;
            }
            catch (Exception ex)
            {
                return Fail($"Could not serialize Unity object identity: {ex.Message}", out message);
            }
        }

        private static bool TrySerializeDictionary(
            IDictionary dictionary,
            Type type,
            int depth,
            HashSet<object> visited,
            out ExecuteScriptValue serialized,
            out string message)
        {
            serialized = NewValue("dictionary", type);
            if (!TryEnter(dictionary, visited, out message))
                return false;
            try
            {
                foreach (DictionaryEntry entry in dictionary)
                {
                    if (serialized.entries.Count >= MaxItems)
                        return Fail("Dictionary result exceeds the item limit.", out message);
                    if (!TrySerializeEntry(entry, depth, visited, out var item, out message))
                        return false;
                    serialized.entries.Add(item);
                }
                serialized.entries = serialized.entries.OrderBy(EntryKey, StringComparer.Ordinal).ToList();
                return true;
            }
            finally
            {
                visited.Remove(dictionary);
            }
        }

        private static bool TrySerializeEntry(
            DictionaryEntry entry,
            int depth,
            HashSet<object> visited,
            out ExecuteScriptDictionaryEntry serialized,
            out string message)
        {
            serialized = null;
            if (!TrySerializeValue(entry.Key, true, depth + 1, visited, out var key, out message))
                return false;
            if (!TrySerializeValue(entry.Value, true, depth + 1, visited, out var value, out message))
                return false;
            serialized = new ExecuteScriptDictionaryEntry { key = key, value = value };
            return true;
        }

        private static bool TrySerializeCollection(
            IEnumerable collection,
            Type type,
            int depth,
            HashSet<object> visited,
            out ExecuteScriptValue serialized,
            out string message)
        {
            serialized = NewValue("collection", type);
            if (!TryEnter(collection, visited, out message))
                return false;
            try
            {
                foreach (var item in collection)
                {
                    if (serialized.items.Count >= MaxItems)
                        return Fail("Collection result exceeds the item limit.", out message);
                    if (!TrySerializeValue(
                        item, true, depth + 1, visited, out var child, out message))
                    {
                        return false;
                    }
                    serialized.items.Add(child);
                }
                return true;
            }
            finally
            {
                visited.Remove(collection);
            }
        }

        private static bool TrySerializeDto(
            object value,
            Type type,
            int depth,
            HashSet<object> visited,
            out ExecuteScriptValue serialized,
            out string message)
        {
            serialized = NewValue("dto", type);
            var fields = type.GetFields(BindingFlags.Instance | BindingFlags.Public)
                .Where(field => !field.IsStatic)
                .OrderBy(field => field.Name, StringComparer.Ordinal)
                .ToArray();
            if (fields.Length == 0)
                return Fail($"Unsupported result type: {type.FullName}", out message);
            if (!TryEnter(value, visited, out message))
                return false;
            try
            {
                foreach (var field in fields)
                {
                    if (!TrySerializeValue(
                        field.GetValue(value), true, depth + 1, visited, out var child, out message))
                    {
                        return false;
                    }
                    serialized.fields.Add(new ExecuteScriptNamedValue
                    {
                        name = field.Name,
                        value = child,
                    });
                }
                return true;
            }
            finally
            {
                visited.Remove(value);
            }
        }

        private static bool MatchesSchema(
            ExecuteScriptValue value,
            bool resultSet,
            string schema,
            out string message)
        {
            var expected = string.IsNullOrEmpty(schema) ? "auto" : schema;
            if (expected == "auto")
            {
                message = "";
                return true;
            }
            var matches = expected == "void"
                ? !resultSet
                : expected == "scalar"
                    ? IsScalar(value.kind)
                    : value.kind == expected;
            if (matches)
            {
                message = "";
                return true;
            }
            return Fail(
                $"Result kind '{value.kind}' does not match requested return schema '{expected}'.",
                out message);
        }

        private static bool IsScalar(string kind)
        {
            return kind == "null" || kind == "boolean" || kind == "integer"
                || kind == "number" || kind == "string" || kind == "enum";
        }

        private static bool IsInteger(Type type)
        {
            return type == typeof(sbyte) || type == typeof(byte)
                || type == typeof(short) || type == typeof(ushort)
                || type == typeof(int) || type == typeof(uint)
                || type == typeof(long) || type == typeof(ulong);
        }

        private static bool IsNumber(Type type)
        {
            return type == typeof(float) || type == typeof(double) || type == typeof(decimal);
        }

        private static string ObjectId(UnityEngine.Object value)
        {
#if UNITY_6000_5_OR_NEWER
            return value.GetEntityId().ToString();
#else
            return value.GetInstanceID().ToString(CultureInfo.InvariantCulture);
#endif
        }

        private static ExecuteScriptValue NewValue(string kind, Type type)
        {
            return new ExecuteScriptValue
            {
                kind = kind,
                type = type?.FullName ?? "",
            };
        }

        private static bool TryEnter(object value, HashSet<object> visited, out string message)
        {
            if (value.GetType().IsValueType || visited.Add(value))
            {
                message = "";
                return true;
            }
            return Fail("Result contains a cyclic object graph.", out message);
        }

        private static string EntryKey(ExecuteScriptDictionaryEntry entry)
        {
            return $"{entry.key.type}:{entry.key.kind}:{entry.key.stringValue}";
        }

        private static bool Fail(string error, out string message)
        {
            message = error;
            return false;
        }

        private sealed class ReferenceComparer : IEqualityComparer<object>
        {
            public static readonly ReferenceComparer Instance = new ReferenceComparer();
            public new bool Equals(object left, object right) => ReferenceEquals(left, right);
            public int GetHashCode(object value) => RuntimeHelpers.GetHashCode(value);
        }
    }
}

using System;
using System.Globalization;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Helper methods for reading and writing SerializedProperty values.
    /// Extracted to keep the command handler under 500 LOC.
    /// </summary>
    public static class SerializedPropertyHelpers
    {
        /// <summary>
        /// Read a SerializedProperty value as a human-readable string.
        /// </summary>
        public static string GetPropertyValueString(SerializedProperty prop)
        {
            switch (prop.propertyType)
            {
                case SerializedPropertyType.Integer:
                    return prop.intValue.ToString();
                case SerializedPropertyType.Boolean:
                    return prop.boolValue.ToString().ToLower();
                case SerializedPropertyType.Float:
                    return prop.floatValue.ToString(CultureInfo.InvariantCulture);
                case SerializedPropertyType.String:
                    return prop.stringValue;
                case SerializedPropertyType.Color:
                    return JsonUtility.ToJson(prop.colorValue);
                case SerializedPropertyType.ObjectReference:
                    return GetObjectReferenceString(prop);
                case SerializedPropertyType.LayerMask:
                    return prop.intValue.ToString();
                case SerializedPropertyType.Enum:
                    return GetEnumString(prop);
                case SerializedPropertyType.Vector2:
                    return JsonUtility.ToJson(prop.vector2Value);
                case SerializedPropertyType.Vector3:
                    return JsonUtility.ToJson(prop.vector3Value);
                case SerializedPropertyType.Vector4:
                    return JsonUtility.ToJson(prop.vector4Value);
                case SerializedPropertyType.Rect:
                    return JsonUtility.ToJson(prop.rectValue);
                case SerializedPropertyType.ArraySize:
                    return prop.intValue.ToString();
                case SerializedPropertyType.Character:
                    return ((char)prop.intValue).ToString();
                case SerializedPropertyType.AnimationCurve:
                    return prop.animationCurveValue != null
                        ? $"AnimationCurve(keys={prop.animationCurveValue.length})"
                        : "null";
                case SerializedPropertyType.Bounds:
                    return JsonUtility.ToJson(prop.boundsValue);
                case SerializedPropertyType.Quaternion:
                    return JsonUtility.ToJson(prop.quaternionValue);
                case SerializedPropertyType.Vector2Int:
                    return JsonUtility.ToJson(prop.vector2IntValue);
                case SerializedPropertyType.Vector3Int:
                    return JsonUtility.ToJson(prop.vector3IntValue);
                case SerializedPropertyType.RectInt:
                    return JsonUtility.ToJson(prop.rectIntValue);
                case SerializedPropertyType.BoundsInt:
                    return JsonUtility.ToJson(prop.boundsIntValue);
                case SerializedPropertyType.Hash128:
                    return prop.hash128Value.ToString();
                default:
                    return $"<{prop.propertyType}>";
            }
        }

        /// <summary>
        /// Set a SerializedProperty value from a JSON string.
        /// Returns true if the value was set successfully.
        /// </summary>
        public static bool SetPropertyValue(SerializedProperty prop, string valueJson)
        {
            try
            {
                switch (prop.propertyType)
                {
                    case SerializedPropertyType.Integer:
                    case SerializedPropertyType.ArraySize:
                        prop.intValue = int.Parse(valueJson.Trim());
                        return true;
                    case SerializedPropertyType.Boolean:
                        prop.boolValue = bool.Parse(valueJson.Trim());
                        return true;
                    case SerializedPropertyType.Float:
                        prop.floatValue = float.Parse(valueJson.Trim(), CultureInfo.InvariantCulture);
                        return true;
                    case SerializedPropertyType.String:
                        prop.stringValue = StripJsonQuotes(valueJson);
                        return true;
                    case SerializedPropertyType.Color:
                        prop.colorValue = JsonUtility.FromJson<Color>(valueJson);
                        return true;
                    case SerializedPropertyType.LayerMask:
                        prop.intValue = int.Parse(valueJson.Trim());
                        return true;
                    case SerializedPropertyType.Enum:
                        return SetEnumValue(prop, valueJson);
                    case SerializedPropertyType.Vector2:
                        prop.vector2Value = JsonUtility.FromJson<Vector2>(valueJson);
                        return true;
                    case SerializedPropertyType.Vector3:
                        prop.vector3Value = JsonUtility.FromJson<Vector3>(valueJson);
                        return true;
                    case SerializedPropertyType.Vector4:
                        prop.vector4Value = JsonUtility.FromJson<Vector4>(valueJson);
                        return true;
                    case SerializedPropertyType.Rect:
                        prop.rectValue = JsonUtility.FromJson<Rect>(valueJson);
                        return true;
                    case SerializedPropertyType.Bounds:
                        prop.boundsValue = JsonUtility.FromJson<Bounds>(valueJson);
                        return true;
                    case SerializedPropertyType.Quaternion:
                        prop.quaternionValue = JsonUtility.FromJson<Quaternion>(valueJson);
                        return true;
                    case SerializedPropertyType.Vector2Int:
                        prop.vector2IntValue = JsonUtility.FromJson<Vector2Int>(valueJson);
                        return true;
                    case SerializedPropertyType.Vector3Int:
                        prop.vector3IntValue = JsonUtility.FromJson<Vector3Int>(valueJson);
                        return true;
                    case SerializedPropertyType.Character:
                        var ch = StripJsonQuotes(valueJson);
                        if (ch.Length > 0) prop.intValue = ch[0];
                        return true;
                    default:
                        BridgeLogger.LogWarning(
                            $"Unsupported property type for set: {prop.propertyType}");
                        return false;
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError(
                    $"Failed to set property {prop.propertyPath}: {ex.Message}");
                return false;
            }
        }

        private static string GetObjectReferenceString(SerializedProperty prop)
        {
            if (prop.objectReferenceValue == null)
                return "null";
            var obj = prop.objectReferenceValue;
            return $"{obj.name} ({obj.GetType().Name})";
        }

        private static string GetEnumString(SerializedProperty prop)
        {
            if (prop.enumValueIndex >= 0
                && prop.enumValueIndex < prop.enumDisplayNames.Length)
            {
                return prop.enumDisplayNames[prop.enumValueIndex];
            }
            return prop.enumValueIndex.ToString();
        }

        private static bool SetEnumValue(SerializedProperty prop, string valueJson)
        {
            string val = StripJsonQuotes(valueJson).Trim();

            // Try as integer index first
            if (int.TryParse(val, out int idx))
            {
                prop.enumValueIndex = idx;
                return true;
            }

            // Try as display name or enum name
            for (int i = 0; i < prop.enumDisplayNames.Length; i++)
            {
                if (string.Equals(prop.enumDisplayNames[i], val,
                    StringComparison.OrdinalIgnoreCase))
                {
                    prop.enumValueIndex = i;
                    return true;
                }
            }
            return false;
        }

        private static string StripJsonQuotes(string value)
        {
            if (value != null && value.Length >= 2
                && value[0] == '"' && value[value.Length - 1] == '"')
            {
                return value.Substring(1, value.Length - 2);
            }
            return value ?? string.Empty;
        }
    }
}

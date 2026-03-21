using System;
using System.Collections.Generic;
using System.IO;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Per-importer-type Extract/Apply helpers for ImportSettingsCommandHandler.
    /// Extracted to keep each file under 500 LOC.
    /// </summary>
    public partial class ImportSettingsCommandHandler
    {
        // -----------------------------------------------------------------------
        // Texture settings
        // -----------------------------------------------------------------------

        private static Dictionary<string, string> ExtractTextureSettings(TextureImporter ti)
        {
            return new Dictionary<string, string>
            {
                ["textureType"] = ti.textureType.ToString(),
                ["textureShape"] = ti.textureShape.ToString(),
                ["sRGBTexture"] = ti.sRGBTexture.ToString(),
                ["alphaSource"] = ti.alphaSource.ToString(),
                ["alphaIsTransparency"] = ti.alphaIsTransparency.ToString(),
                ["maxTextureSize"] = ti.maxTextureSize.ToString(),
                ["textureCompression"] = ti.textureCompression.ToString(),
                ["compressionQuality"] = ti.compressionQuality.ToString(),
                ["filterMode"] = ti.filterMode.ToString(),
                ["anisoLevel"] = ti.anisoLevel.ToString(),
                ["wrapMode"] = ti.wrapMode.ToString(),
                ["mipmapEnabled"] = ti.mipmapEnabled.ToString(),
                ["streamingMipmaps"] = ti.streamingMipmaps.ToString(),
                ["isReadable"] = ti.isReadable.ToString(),
                ["npotScale"] = ti.npotScale.ToString(),
            };
        }

        private static List<string> ApplyTextureSettings(
            TextureImporter ti, Dictionary<string, string> settings)
        {
            var applied = new List<string>();
            foreach (var kv in settings)
            {
                try
                {
                    switch (kv.Key)
                    {
                        case "maxTextureSize":
                            ti.maxTextureSize = int.Parse(kv.Value);
                            applied.Add(kv.Key);
                            break;
                        case "textureCompression":
                            ti.textureCompression = Enum.Parse<TextureImporterCompression>(kv.Value);
                            applied.Add(kv.Key);
                            break;
                        case "mipmapEnabled":
                            ti.mipmapEnabled = bool.Parse(kv.Value);
                            applied.Add(kv.Key);
                            break;
                        case "filterMode":
                            ti.filterMode = Enum.Parse<FilterMode>(kv.Value);
                            applied.Add(kv.Key);
                            break;
                        case "sRGBTexture":
                            ti.sRGBTexture = bool.Parse(kv.Value);
                            applied.Add(kv.Key);
                            break;
                        case "anisoLevel":
                            ti.anisoLevel = int.Parse(kv.Value);
                            applied.Add(kv.Key);
                            break;
                        case "isReadable":
                            ti.isReadable = bool.Parse(kv.Value);
                            applied.Add(kv.Key);
                            break;
                        case "streamingMipmaps":
                            ti.streamingMipmaps = bool.Parse(kv.Value);
                            applied.Add(kv.Key);
                            break;
                        case "wrapMode":
                            ti.wrapMode = Enum.Parse<TextureWrapMode>(kv.Value);
                            applied.Add(kv.Key);
                            break;
                        case "alphaIsTransparency":
                            ti.alphaIsTransparency = bool.Parse(kv.Value);
                            applied.Add(kv.Key);
                            break;
                        case "npotScale":
                            ti.npotScale = Enum.Parse<TextureImporterNPOTScale>(kv.Value);
                            applied.Add(kv.Key);
                            break;
                    }
                }
                catch (Exception ex)
                {
                    BridgeLogger.LogWarning($"Failed to apply {kv.Key}={kv.Value}: {ex.Message}");
                }
            }
            return applied;
        }

        // -----------------------------------------------------------------------
        // Model settings
        // -----------------------------------------------------------------------

        private static Dictionary<string, string> ExtractModelSettings(ModelImporter mi)
        {
            return new Dictionary<string, string>
            {
                ["globalScale"] = mi.globalScale.ToString("G"),
                ["useFileScale"] = mi.useFileScale.ToString(),
                ["meshCompression"] = mi.meshCompression.ToString(),
                ["isReadable"] = mi.isReadable.ToString(),
                ["importBlendShapes"] = mi.importBlendShapes.ToString(),
                ["importNormals"] = mi.importNormals.ToString(),
                ["importTangents"] = mi.importTangents.ToString(),
                ["importAnimation"] = mi.importAnimation.ToString(),
                ["animationType"] = mi.animationType.ToString(),
                ["importCameras"] = mi.importCameras.ToString(),
                ["importLights"] = mi.importLights.ToString(),
            };
        }

        private static List<string> ApplyModelSettings(
            ModelImporter mi, Dictionary<string, string> settings)
        {
            var applied = new List<string>();
            foreach (var kv in settings)
            {
                try
                {
                    switch (kv.Key)
                    {
                        case "globalScale":
                            mi.globalScale = float.Parse(kv.Value);
                            applied.Add(kv.Key);
                            break;
                        case "isReadable":
                            mi.isReadable = bool.Parse(kv.Value);
                            applied.Add(kv.Key);
                            break;
                        case "importAnimation":
                            mi.importAnimation = bool.Parse(kv.Value);
                            applied.Add(kv.Key);
                            break;
                        case "importCameras":
                            mi.importCameras = bool.Parse(kv.Value);
                            applied.Add(kv.Key);
                            break;
                        case "importLights":
                            mi.importLights = bool.Parse(kv.Value);
                            applied.Add(kv.Key);
                            break;
                        case "importBlendShapes":
                            mi.importBlendShapes = bool.Parse(kv.Value);
                            applied.Add(kv.Key);
                            break;
                    }
                }
                catch (Exception ex)
                {
                    BridgeLogger.LogWarning($"Failed to apply {kv.Key}={kv.Value}: {ex.Message}");
                }
            }
            return applied;
        }

        // -----------------------------------------------------------------------
        // Audio settings
        // -----------------------------------------------------------------------

        private static Dictionary<string, string> ExtractAudioSettings(AudioImporter ai)
        {
            return new Dictionary<string, string>
            {
                ["forceToMono"] = ai.forceToMono.ToString(),
                ["loadInBackground"] = ai.loadInBackground.ToString(),
                ["ambisonic"] = ai.ambisonic.ToString(),
            };
        }

        private static List<string> ApplyAudioSettings(
            AudioImporter ai, Dictionary<string, string> settings)
        {
            var applied = new List<string>();
            foreach (var kv in settings)
            {
                try
                {
                    switch (kv.Key)
                    {
                        case "forceToMono":
                            ai.forceToMono = bool.Parse(kv.Value);
                            applied.Add(kv.Key);
                            break;
                        case "loadInBackground":
                            ai.loadInBackground = bool.Parse(kv.Value);
                            applied.Add(kv.Key);
                            break;
                        case "ambisonic":
                            ai.ambisonic = bool.Parse(kv.Value);
                            applied.Add(kv.Key);
                            break;
                        // preloadAudioData is obsolete in Unity 6
                        // Use AudioImporter.SampleSettings per-platform instead
                    }
                }
                catch (Exception ex)
                {
                    BridgeLogger.LogWarning($"Failed to apply {kv.Key}={kv.Value}: {ex.Message}");
                }
            }
            return applied;
        }

        // -----------------------------------------------------------------------
        // Generic settings
        // -----------------------------------------------------------------------

        private static Dictionary<string, string> ExtractGenericSettings(AssetImporter importer)
        {
            return new Dictionary<string, string>
            {
                ["userData"] = importer.userData ?? "",
                ["assetBundleName"] = importer.assetBundleName ?? "",
                ["assetBundleVariant"] = importer.assetBundleVariant ?? "",
            };
        }

        private static List<string> ApplyGenericSettings(
            AssetImporter importer, Dictionary<string, string> settings)
        {
            var applied = new List<string>();
            foreach (var kv in settings)
            {
                switch (kv.Key)
                {
                    case "userData":
                        importer.userData = kv.Value;
                        applied.Add(kv.Key);
                        break;
                    case "assetBundleName":
                        importer.assetBundleName = kv.Value;
                        applied.Add(kv.Key);
                        break;
                    case "assetBundleVariant":
                        importer.assetBundleVariant = kv.Value;
                        applied.Add(kv.Key);
                        break;
                }
            }
            return applied;
        }

        // -----------------------------------------------------------------------
        // Validation and utility helpers
        // -----------------------------------------------------------------------

        private static bool IsValidTemplateName(string name)
        {
            return !string.IsNullOrEmpty(name)
                && name.Length <= 64
                && Regex.IsMatch(name, @"^[a-zA-Z0-9_-]+$");
        }

        private static bool MatchesGlob(string path, string glob)
        {
            var fileName = Path.GetFileName(path);
            var pattern = "^" + Regex.Escape(glob).Replace("\\*", ".*").Replace("\\?", ".") + "$";
            return Regex.IsMatch(fileName, pattern, RegexOptions.IgnoreCase);
        }

        private static Dictionary<string, string> ParseSettingsJson(string json)
        {
            var result = new Dictionary<string, string>();
            if (string.IsNullOrEmpty(json)) return result;

            var dict = JsonUtility.FromJson<SerializableDict>(json);
            if (dict is not null)
            {
                for (int i = 0; i < dict.keys.Count && i < dict.values.Count; i++)
                    result[dict.keys[i]] = dict.values[i];
            }
            return result;
        }

        private static BridgeResponse RequiredError(
            BridgeCommand command, string field, string operation)
        {
            return BridgeResponse.Error(
                command.commandId, command.commandType,
                $"{field} is required for '{operation}' operation"
            );
        }

        private static BridgeResponse AssetNotFoundError(BridgeCommand command, string path)
        {
            return BridgeResponse.Error(
                command.commandId, command.commandType,
                $"Asset not found or no importer: {path}"
            );
        }

        private static BridgeResponse PlayModeError(BridgeCommand command)
        {
            return BridgeResponse.Error(
                command.commandId, command.commandType,
                "Cannot modify import settings during play mode."
            );
        }

        private static BridgeResponse InvalidNameError(BridgeCommand command, string name)
        {
            return BridgeResponse.Error(
                command.commandId, command.commandType,
                $"Invalid template name: '{name}'. "
                + "Must be alphanumeric with hyphens/underscores, max 64 characters."
            );
        }
    }

    /// <summary>
    /// Serializable key-value dictionary for JsonUtility compatibility.
    /// </summary>
    [Serializable]
    public class SerializableDict
    {
        public List<string> keys = new List<string>();
        public List<string> values = new List<string>();

        public SerializableDict() { }

        public SerializableDict(Dictionary<string, string> dict)
        {
            foreach (var kv in dict)
            {
                keys.Add(kv.Key);
                values.Add(kv.Value);
            }
        }
    }
}

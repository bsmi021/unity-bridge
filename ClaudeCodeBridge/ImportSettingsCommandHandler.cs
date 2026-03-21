using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for asset import settings operations.
    ///
    /// PURPOSE:
    /// Read, modify, and template-ize import settings for textures, models, audio,
    /// and generic assets. Supports bulk operations across folders.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "get" - Get current import settings for an asset
    /// 2. "set" - Modify import settings and reimport
    /// 3. "reimport" - Reimport asset with current settings
    /// 4. "bulk-set" - Apply settings to all matching assets in a folder
    /// 5. "template-save" - Save current settings as a named template
    /// 6. "template-apply" - Apply a saved template to an asset
    ///
    /// GUARDS:
    /// - EditorApplication.isCompiling: blocks all operations
    /// - EditorApplication.isPlaying: blocks mutating operations (set, reimport, bulk-set, template-apply)
    /// </summary>
    public partial class ImportSettingsCommandHandler : ICommandHandler
    {
        public string CommandType => "import-settings-operation";

        private static readonly string TEMPLATES_DIR = ".claude/unity/import-templates";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(
                        command.commandId, command.commandType,
                        "Cannot modify import settings while scripts are compiling."
                    );
                }

                var parameters = JsonUtility.FromJson<ImportSettingsParams>(
                    command.parametersJson ?? "{}"
                );
                if (parameters == null)
                    parameters = new ImportSettingsParams();

                BridgeLogger.LogDebug($"Executing import-settings operation: {parameters.operation}");

                switch (parameters.operation?.ToLower())
                {
                    case "get":
                        return ExecuteGet(command, parameters);
                    case "set":
                        return ExecuteSet(command, parameters);
                    case "reimport":
                        return ExecuteReimport(command, parameters);
                    case "bulk-set":
                        return ExecuteBulkSet(command, parameters);
                    case "template-save":
                        return ExecuteTemplateSave(command, parameters);
                    case "template-apply":
                        return ExecuteTemplateApply(command, parameters);
                    default:
                        return BridgeResponse.Error(
                            command.commandId, command.commandType,
                            $"Unknown operation: {parameters.operation}. "
                            + "Supported: get, set, reimport, bulk-set, template-save, template-apply"
                        );
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Import settings error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse ExecuteGet(BridgeCommand command, ImportSettingsParams p)
        {
            if (string.IsNullOrEmpty(p.assetPath))
                return RequiredError(command, "assetPath", "get");

            var importer = AssetImporter.GetAtPath(p.assetPath);
            if (importer is null)
                return AssetNotFoundError(command, p.assetPath);

            var importerType = GetImporterTypeName(importer);
            var settings = ExtractSettings(importer);

            var result = new ImportSettingsGetResult
            {
                operation = "get",
                assetPath = p.assetPath,
                importerType = importerType,
                settingsJson = JsonUtility.ToJson(new SerializableDict(settings)),
                success = true,
                message = $"Import settings retrieved for {importerType}"
            };

            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result)
            );
        }

        private BridgeResponse ExecuteSet(BridgeCommand command, ImportSettingsParams p)
        {
            if (EditorApplication.isPlaying)
                return PlayModeError(command);
            if (string.IsNullOrEmpty(p.assetPath))
                return RequiredError(command, "assetPath", "set");
            if (string.IsNullOrEmpty(p.settings))
                return RequiredError(command, "settings", "set");

            var importer = AssetImporter.GetAtPath(p.assetPath);
            if (importer is null)
                return AssetNotFoundError(command, p.assetPath);

            var settingsDict = ParseSettingsJson(p.settings);
            var applied = ApplySettings(importer, settingsDict);
            importer.SaveAndReimport();

            var result = new ImportSettingsSetResult
            {
                operation = "set",
                assetPath = p.assetPath,
                importerType = GetImporterTypeName(importer),
                updatedCount = applied.Count,
                reimported = true,
                success = true,
                message = $"Updated {applied.Count} settings and reimported asset"
            };
            result.updatedSettings.AddRange(applied);

            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result)
            );
        }

        private BridgeResponse ExecuteReimport(BridgeCommand command, ImportSettingsParams p)
        {
            if (EditorApplication.isPlaying)
                return PlayModeError(command);
            if (string.IsNullOrEmpty(p.assetPath))
                return RequiredError(command, "assetPath", "reimport");

            var importer = AssetImporter.GetAtPath(p.assetPath);
            if (importer is null)
                return AssetNotFoundError(command, p.assetPath);

            var options = p.force
                ? ImportAssetOptions.ForceUpdate
                : ImportAssetOptions.Default;
            AssetDatabase.ImportAsset(p.assetPath, options);

            var result = new ImportSettingsReimportResult
            {
                operation = "reimport",
                assetPath = p.assetPath,
                importerType = GetImporterTypeName(importer),
                success = true,
                message = "Asset reimported successfully"
            };

            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result)
            );
        }

        private BridgeResponse ExecuteBulkSet(BridgeCommand command, ImportSettingsParams p)
        {
            if (EditorApplication.isPlaying)
                return PlayModeError(command);
            if (string.IsNullOrEmpty(p.folderPath))
                return RequiredError(command, "folderPath", "bulk-set");
            if (string.IsNullOrEmpty(p.settings))
                return RequiredError(command, "settings", "bulk-set");

            var settingsDict = ParseSettingsJson(p.settings);
            var guids = AssetDatabase.FindAssets("", new[] { p.folderPath });

            var result = new ImportSettingsBulkSetResult
            {
                operation = "bulk-set",
                folderPath = p.folderPath,
                filter = p.filter ?? ""
            };

            foreach (var guid in guids)
            {
                var assetPath = AssetDatabase.GUIDToAssetPath(guid);
                if (AssetDatabase.IsValidFolder(assetPath)) continue;

                if (!string.IsNullOrEmpty(p.filter) && !MatchesGlob(assetPath, p.filter))
                    continue;

                var importer = AssetImporter.GetAtPath(assetPath);
                if (importer is null)
                {
                    result.skippedAssets.Add(assetPath);
                    result.skippedCount++;
                    continue;
                }

                var applied = ApplySettings(importer, settingsDict);
                if (applied.Count > 0)
                {
                    importer.SaveAndReimport();
                    result.updatedAssets.Add(assetPath);
                    result.updatedCount++;
                }
                else
                {
                    result.skippedAssets.Add(assetPath);
                    result.skippedCount++;
                }
            }

            result.success = true;
            result.message = $"Updated {result.updatedCount} assets in {p.folderPath}"
                + (string.IsNullOrEmpty(p.filter) ? "" : $" matching {p.filter}");

            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result)
            );
        }

        private BridgeResponse ExecuteTemplateSave(BridgeCommand command, ImportSettingsParams p)
        {
            if (string.IsNullOrEmpty(p.templateName))
                return RequiredError(command, "templateName", "template-save");
            if (string.IsNullOrEmpty(p.assetPath))
                return RequiredError(command, "assetPath", "template-save");
            if (!IsValidTemplateName(p.templateName))
                return InvalidNameError(command, p.templateName);

            var importer = AssetImporter.GetAtPath(p.assetPath);
            if (importer is null)
                return AssetNotFoundError(command, p.assetPath);

            var settings = ExtractSettings(importer);
            var template = new ImportTemplate
            {
                name = p.templateName,
                importerType = GetImporterTypeName(importer),
                createdAt = DateTime.UtcNow.ToString("o"),
                sourceAsset = p.assetPath,
                settingsJson = JsonUtility.ToJson(new SerializableDict(settings))
            };

            var dir = Path.Combine(Application.dataPath, "..", TEMPLATES_DIR);
            Directory.CreateDirectory(dir);
            var filePath = Path.Combine(dir, $"{p.templateName}.json");
            File.WriteAllText(filePath, JsonUtility.ToJson(template));

            var result = new ImportSettingsTemplateSaveResult
            {
                operation = "template-save",
                templateName = p.templateName,
                importerType = template.importerType,
                templatePath = $"{TEMPLATES_DIR}/{p.templateName}.json",
                success = true,
                message = $"Template '{p.templateName}' saved from {template.importerType} settings"
            };

            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result)
            );
        }

        private BridgeResponse ExecuteTemplateApply(BridgeCommand command, ImportSettingsParams p)
        {
            if (EditorApplication.isPlaying)
                return PlayModeError(command);
            if (string.IsNullOrEmpty(p.templateName))
                return RequiredError(command, "templateName", "template-apply");
            if (string.IsNullOrEmpty(p.assetPath))
                return RequiredError(command, "assetPath", "template-apply");

            var dir = Path.Combine(Application.dataPath, "..", TEMPLATES_DIR);
            var filePath = Path.Combine(dir, $"{p.templateName}.json");
            if (!File.Exists(filePath))
            {
                return BridgeResponse.Error(
                    command.commandId, command.commandType,
                    $"Template not found: {p.templateName}"
                );
            }

            var templateJson = File.ReadAllText(filePath);
            var template = JsonUtility.FromJson<ImportTemplate>(templateJson);

            var importer = AssetImporter.GetAtPath(p.assetPath);
            if (importer is null)
                return AssetNotFoundError(command, p.assetPath);

            var importerType = GetImporterTypeName(importer);
            if (importerType != template.importerType)
            {
                return BridgeResponse.Error(
                    command.commandId, command.commandType,
                    $"Template type mismatch: template is {template.importerType} "
                    + $"but asset uses {importerType}"
                );
            }

            var settingsDict = ParseSettingsJson(template.settingsJson);
            var applied = ApplySettings(importer, settingsDict);
            importer.SaveAndReimport();

            var result = new ImportSettingsTemplateApplyResult
            {
                operation = "template-apply",
                templateName = p.templateName,
                assetPath = p.assetPath,
                importerType = importerType,
                appliedCount = applied.Count,
                reimported = true,
                success = true,
                message = $"Template '{p.templateName}' applied to asset and reimported"
            };
            result.appliedSettings.AddRange(applied);

            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result)
            );
        }

        // -----------------------------------------------------------------------
        // Importer type helpers
        // -----------------------------------------------------------------------

        private static string GetImporterTypeName(AssetImporter importer)
        {
            return importer switch
            {
                TextureImporter => "TextureImporter",
                ModelImporter => "ModelImporter",
                AudioImporter => "AudioImporter",
                _ => "AssetImporter"
            };
        }

        private static Dictionary<string, string> ExtractSettings(AssetImporter importer)
        {
            return importer switch
            {
                TextureImporter ti => ExtractTextureSettings(ti),
                ModelImporter mi => ExtractModelSettings(mi),
                AudioImporter ai => ExtractAudioSettings(ai),
                _ => ExtractGenericSettings(importer)
            };
        }

        private static List<string> ApplySettings(
            AssetImporter importer, Dictionary<string, string> settings)
        {
            return importer switch
            {
                TextureImporter ti => ApplyTextureSettings(ti, settings),
                ModelImporter mi => ApplyModelSettings(mi, settings),
                AudioImporter ai => ApplyAudioSettings(ai, settings),
                _ => ApplyGenericSettings(importer, settings)
            };
        }

        // Per-importer Extract/Apply methods, validation helpers, and SerializableDict
        // are in ImportSettingsHelpers.cs (partial class).
    }
}

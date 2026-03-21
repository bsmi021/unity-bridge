using System;
using System.Collections.Generic;

namespace BWS.Editor.ClaudeCodeBridge
{
    // -----------------------------------------------------------------------
    // Phase 3 models — Import Settings
    // -----------------------------------------------------------------------

    /// <summary>
    /// Parameters for the import-settings-operation command.
    /// </summary>
    [Serializable]
    public class ImportSettingsParams
    {
        public string operation;
        public string assetPath;
        public string settings;
        public bool force;
        public string templateName;
        public string folderPath;
        public string filter;
    }

    /// <summary>
    /// Result data for import-settings get operation.
    /// </summary>
    [Serializable]
    public class ImportSettingsGetResult
    {
        public string operation;
        public string assetPath;
        public string importerType;
        public string settingsJson;
        public bool success;
        public string message;
    }

    /// <summary>
    /// Result data for import-settings set operation.
    /// </summary>
    [Serializable]
    public class ImportSettingsSetResult
    {
        public string operation;
        public string assetPath;
        public string importerType;
        public List<string> updatedSettings = new List<string>();
        public int updatedCount;
        public bool reimported;
        public bool success;
        public string message;
    }

    /// <summary>
    /// Result data for import-settings reimport operation.
    /// </summary>
    [Serializable]
    public class ImportSettingsReimportResult
    {
        public string operation;
        public string assetPath;
        public string importerType;
        public bool success;
        public string message;
    }

    /// <summary>
    /// Result data for import-settings bulk-set operation.
    /// </summary>
    [Serializable]
    public class ImportSettingsBulkSetResult
    {
        public string operation;
        public string folderPath;
        public string filter;
        public List<string> updatedAssets = new List<string>();
        public int updatedCount;
        public int skippedCount;
        public List<string> skippedAssets = new List<string>();
        public bool success;
        public string message;
    }

    /// <summary>
    /// Result data for import-settings template-save operation.
    /// </summary>
    [Serializable]
    public class ImportSettingsTemplateSaveResult
    {
        public string operation;
        public string templateName;
        public string importerType;
        public string templatePath;
        public bool success;
        public string message;
    }

    /// <summary>
    /// Result data for import-settings template-apply operation.
    /// </summary>
    [Serializable]
    public class ImportSettingsTemplateApplyResult
    {
        public string operation;
        public string templateName;
        public string assetPath;
        public string importerType;
        public List<string> appliedSettings = new List<string>();
        public int appliedCount;
        public bool reimported;
        public bool success;
        public string message;
    }

    /// <summary>
    /// Import template JSON file structure (stored on disk).
    /// </summary>
    [Serializable]
    public class ImportTemplate
    {
        public string name;
        public string importerType;
        public string createdAt;
        public string sourceAsset;
        public string settingsJson;
    }
}
